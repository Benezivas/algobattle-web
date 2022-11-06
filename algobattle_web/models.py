"Database models"
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Any, BinaryIO, Mapping, cast, overload
from uuid import UUID, uuid4
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import String, Boolean, Table, ForeignKey, DateTime
from sqlalchemy.orm import relationship, RelationshipProperty as Rel, Mapped, mapped_column
from sqlalchemy_utils import UUIDType
from sqlalchemy_media import StoreManager
from fastapi import UploadFile

from algobattle_web.config import SECRET_KEY, ALGORITHM
from algobattle_web.database import Base, Session, Json, DbFile
from algobattle_web.base_classes import ObjID, Column


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
    email: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    token_id: Mapped[UUID] = mapped_column(UUIDType, default=uuid4)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    teams: Rel[list[Team]] = relationship("Team", secondary=team_members, back_populates="members", lazy="joined")

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
                if isinstance(o["id"], UUID):
                    return self.id == o["id"]
                elif isinstance(o["id"], str):
                    return str(self.id) == o["id"]
        return NotImplemented

    @classmethod
    def get(cls, db: Session, user: UUID | str) -> User | None:
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


class Context(Base):
    name: Mapped[str] = mapped_column(String, unique=True)

    teams: Rel[list[Team]] = relationship("Team", back_populates="context")

    class Schema(Base.Schema):
        name: str

    @classmethod
    def get(cls, db: Session, context: str | UUID) -> Context | None:
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
    name: Mapped[str] = mapped_column(String)
    context_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("contexts.id"))

    context: Rel[Context] = relationship("Context", back_populates="teams", uselist=False, lazy="joined")
    members: Rel[list[User]] = relationship("User", secondary=team_members, back_populates="teams", lazy="joined")

    class Schema(Base.Schema):
        name: str
        context: ObjID
        members: list[ObjID]

    def __str__(self) -> str:
        return self.name

    @overload
    @classmethod
    def get(cls, db: Session, team: UUID) -> Team | None:
        ...

    @overload
    @classmethod
    def get(cls, db: Session, team: str, context: Context) -> Team | None:
        ...

    @classmethod
    def get(cls, db: Session, team: str | UUID, context: Context | None = None) -> Team | None:
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

    def update(self, db: Session, name: str | None = None, context: str | UUID | Context | None = None):
        if name is not None:
            self.name = name
        if context is not None:
            if isinstance(context, (str, UUID)):
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
    name: Mapped[str] = mapped_column(String, unique=True)
    file: Mapped[DbFile] = mapped_column(DbFile.as_mutable(Json))

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
    def get(cls, db: Session, context: UUID | str) -> Config | None:
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
    name: Mapped[str] = mapped_column(String, unique=True)
    file: Mapped[DbFile] = mapped_column(DbFile.as_mutable(Json))
    config_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("configs.id"))
    start: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    end: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    description: Mapped[DbFile | None] = mapped_column(DbFile.as_mutable(Json), default=None)

    config: Rel[Config] = relationship("Config", uselist=False, lazy="joined")

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
    def get(cls, db: Session, problem: UUID | str) -> Problem | None:
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
