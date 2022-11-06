"Database models"
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Any, BinaryIO, Mapping, cast, overload
from enum import Enum
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Table, ForeignKey, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy_media import StoreManager
from fastapi import UploadFile
from uuid import UUID

from algobattle_web.config import SECRET_KEY, ALGORITHM
from algobattle_web.database import Base, Session, DbFile, ID
from algobattle_web.base_classes import ObjID


class ModelError(Exception):
    pass


@dataclass
class ValueTaken(ModelError):
    value: str


@dataclass
class ResourceNeeded(ModelError):
    err: str | None = None


team_members = Table(
    "team_members",
    Base.metadata,
    Column("team", ForeignKey("teams.id"), primary_key=True),
    Column("user", ForeignKey("users.id"), primary_key=True),
)


class User(Base):
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    token_id: Mapped[ID]
    is_admin: Mapped[bool] = mapped_column(default=False)

    teams: Mapped[list[Team]] = relationship(secondary=team_members, back_populates="members", lazy="joined")
    settings: Mapped[UserSettings] = relationship(back_populates="user", lazy="joined")

    class Schema(Base.Schema):
        name: str
        email: str
        is_admin: bool
        teams: list[ObjID]

    def __eq__(self, o: object) -> bool:
        if isinstance(o, User):
            return self.id == o.id
        elif isinstance(o, Mapping):
            if "id" in o:
                if isinstance(o["id"], ID):
                    return self.id == o["id"]
                elif isinstance(o["id"], str):
                    return str(self.id) == o["id"]
        return NotImplemented

    @classmethod
    def get(cls, db: Session, user: ID | str) -> User | None:
        """Queries the user db by either the user id or their email."""
        filter_type = cls.email if isinstance(user, str) else cls.id
        return db.query(cls).filter(filter_type == user).first()

    @classmethod
    def create(cls, db: Session, email: str, name: str, is_admin: bool = False) -> User:
        """Creates a new user, raises `EmailTaken` if the email is already in use."""
        if cls.get(db, email) is not None:
            raise ValueTaken(email)
        new_user = cls(email=email, name=name, is_admin=is_admin)
        db.add(new_user)
        db.add(UserSettings(user_id=new_user.id))
        db.commit()
        db.refresh(new_user)
        return new_user

    def update(self, db: Session, email: str | None = None, name: str | None = None, is_admin: bool | None = None) -> User:
        if email:
            email_user = self.get(db, email)
            if email_user is not None and email_user != self:
                raise ValueTaken(email)
            else:
                self.email = email
        if name:
            self.name = name
        if is_admin is not None:
            self.is_admin = is_admin
        db.commit()
        return self

    def cookie(self) -> dict[str, Any]:
        payload = {
            "type": "user",
            "user_id": self.id.hex,
            "token_id": self.token_id.hex,
            "exp": datetime.now() + timedelta(weeks=4),
        }
        return {"key": "user_token", "value": jwt.encode(payload, SECRET_KEY, ALGORITHM)}

    @classmethod
    def decode_token(cls, db: Session, token: str | None) -> User | None:
        if token is None:
            return
        try:
            payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
            if payload["type"] == "user":
                user_id = UUID(cast(str, payload["user_id"]))
                token_id = UUID(cast(str, payload["token_id"]))
                user = cls.get(db, user_id)
                if user is not None and user.token_id == token_id:
                    return user
        except (JWTError, ExpiredSignatureError, NameError):
            return


class UserSettings(Base):
    __tablename__ = "usersettings"  # type: ignore
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    selected_team_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"), default=None)

    user: Mapped[User] = relationship(back_populates="settings", lazy="joined")
    selected_team: Mapped[Team | None] = relationship(lazy="joined")

    class Schema(Base.Schema):
        selected_team: ObjID | None


class Context(Base):
    name: Mapped[str] = mapped_column(unique=True)

    teams: Mapped[list[Team]] = relationship(back_populates="context")

    class Schema(Base.Schema):
        name: str

    @classmethod
    def get(cls, db: Session, context: str | ID) -> Context | None:
        row = cls.name if isinstance(context, str) else cls.id
        return db.query(cls).filter(row == context).first()

    @classmethod
    def create(cls, db: Session, name: str) -> Context:
        if cls.get(db, name) is not None:
            raise ValueTaken(name)
        context = Context(name=name)
        db.add(context)
        db.commit()
        db.refresh(context)
        return context

    def update(self, db: Session, name: str | None) -> Context:
        if name is not None:
            self.name = name
            db.commit()
        return self

    def delete(self, db: Session):
        if self.teams:
            raise ResourceNeeded
        db.delete(self)
        db.commit()


class Team(Base):
    name: Mapped[str]
    context_id: Mapped[ID] = mapped_column(ForeignKey("contexts.id"))

    context: Mapped[Context] = relationship(back_populates="teams", uselist=False, lazy="joined")
    members: Mapped[list[User]] = relationship(secondary=team_members, back_populates="teams", lazy="joined")

    class Schema(Base.Schema):
        name: str
        context: ObjID
        members: list[ObjID]

    def __str__(self) -> str:
        return self.name

    @overload
    @classmethod
    def get(cls, db: Session, team: ID) -> Team | None:
        ...

    @overload
    @classmethod
    def get(cls, db: Session, team: str, context: Context) -> Team | None:
        ...

    @classmethod
    def get(cls, db: Session, team: str | ID, context: Context | None = None) -> Team | None:
        if isinstance(team, str):
            if context is None:
                raise ValueError("If the team is given by its name, you have to specify a context!")
            filter_expr = (cls.name == team, cls.context_id == context.id)
        else:
            filter_expr = (cls.id == team,)
        return db.query(cls).filter(*filter_expr).first()

    @classmethod
    def create(cls, db: Session, name: str, context: Context) -> Team:
        if cls.get(db, name, context) is not None:
            raise ValueTaken(name)
        team = cls(name=name, context_id=context.id)
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    def update(self, db: Session, name: str | None = None, context: str | ID | Context | None = None):
        if name is not None:
            self.name = name
        if context is not None:
            if isinstance(context, (str, ID)):
                context = Context.get(db, context)
                if context is None:
                    raise ValueError
            self.context_id = context.id
        db.commit()

    def add_member(self, db: Session, user: User):
        if user in self.members:
            return
        self.members.append(user)
        db.commit()

    def remove_member(self, db: Session, user: User):
        if user not in self.members:
            return
        self.members.remove(user)
        db.commit()


class Config(Base):
    name: Mapped[str] = mapped_column(unique=True)
    file: Mapped[DbFile]

    class Schema(Base.Schema):
        name: str

    @classmethod
    def create(cls, db: Session, name: str, file: BinaryIO | UploadFile):
        if cls.get(db, name) is not None:
            raise ValueTaken(name)
        with StoreManager(db):
            db_file = DbFile()
            db_file.attach(file)
            config = cls(name=name, file=db_file)
            db.add(config)
            db.commit()
        db.refresh(config)
        return config

    @classmethod
    def get(cls, db: Session, context: ID | str) -> Config | None:
        """Queries the db by either its id or name."""
        filter_type = cls.name if isinstance(context, str) else cls.id
        return db.query(cls).filter(filter_type == context).first()

    def update(self, db: Session, name: str | None = None, file: BinaryIO | UploadFile | None = None):
        with StoreManager(db):
            if name is not None:
                self.name = name
            if file is not None:
                self.file.attach(file)
            db.commit()

    def delete(self, db: Session):
        with StoreManager(db):
            db.delete(self)
            db.commit()


class Problem(Base):
    name: Mapped[str] = mapped_column(unique=True)
    file: Mapped[DbFile]
    config_id: Mapped[ID] = mapped_column(ForeignKey("configs.id"))
    start: Mapped[datetime | None] = mapped_column(default=None)
    end: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[DbFile | None] = mapped_column(default=None)

    config: Mapped[Config] = relationship(uselist=False, lazy="joined")

    class Schema(Base.Schema):
        name: str
        file: DbFile.Schema
        config: ObjID
        start: datetime | None
        end: datetime | None
        description: DbFile.Schema | None

    @classmethod
    def create(
        cls,
        db: Session,
        name: str,
        file: BinaryIO | UploadFile,
        config: Config,
        start: datetime | None = None,
        end: datetime | None = None,
        description: BinaryIO | UploadFile | None = None,
    ):
        if cls.get(db, name) is not None:
            raise ValueTaken(name)
        with StoreManager(db):
            db_file = DbFile.create_from(file)
            if description is not None:
                desc_file = DbFile.create_from(description)
            else:
                desc_file = None
            problem = cls(name=name, file=db_file, config=config, start=start, end=end, description=desc_file)
            db.add(problem)
            db.commit()
        db.refresh(problem)
        return problem

    @classmethod
    def get(cls, db: Session, problem: ID | str) -> Problem | None:
        """Queries the db by either its id or name."""
        filter_type = cls.name if isinstance(problem, str) else cls.id
        return db.query(cls).filter(filter_type == problem).first()

    def update(
        self,
        db: Session,
        name: str | None,
        file: BinaryIO | UploadFile | None = None,
        config: Config | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        desc: BinaryIO | UploadFile | None = None,
    ):
        with StoreManager(db):
            if name:
                self.name = name
            if file is not None:
                self.file.attach(file)
            if config is not None:
                self.config_id = config.id
            if start is not None:
                self.start = start
            if end is not None:
                self.end = end
            if desc is not None:
                if self.description is None:
                    self.description = DbFile()
                self.description.attach(desc)
            db.commit()

    def delete(self, db: Session):
        with StoreManager(db):
            db.delete(self)
            db.commit()


class Program(Base):
    name: Mapped[str] = mapped_column(unique=True)
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"))
    role: Mapped[Program.Role]
    file: Mapped[DbFile]
    creation_time: Mapped[datetime] = mapped_column(default=datetime.now)
    problem_id: Mapped[UUID] = mapped_column(ForeignKey("problems.id"))

    team: Mapped[Team] = relationship(lazy="joined")
    problem: Mapped[Team] = relationship(lazy="joined")

    class Role(Enum):
        generator = 0
        solver = 0

    class Schema(Base.Schema):
        name: str
        team: ObjID
        type: Program.Role
        file: DbFile.Schema
        creation_type: datetime
        problem: ObjID

    @classmethod
    def create(cls, db: Session, name: str, team: Team, role: Program.Role, file: BinaryIO | UploadFile, problem: Problem) -> Program:
        if cls.get(db, name) is not None:
            raise ValueTaken(name)
        with StoreManager(db):
            db_file = DbFile.create_from(file)
            program = cls(name=name, team=team, role=role, file=db_file, problem=problem)
            db.add(program)
            db.commit()
        db.refresh(program)
        return program

    @classmethod
    def get(cls, db: Session, prog: ID | str) -> Program | None:
        """Queries the db by either its id or name."""
        filter_type = cls.name if isinstance(prog, str) else cls.id
        return db.query(cls).filter(filter_type == prog).first()


    def delete(self, db: Session):
        with StoreManager(db):
            db.delete(self)
            db.commit()

