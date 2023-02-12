"Database models"
from abc import ABC
from dataclasses import dataclass, InitVar
from datetime import timedelta, datetime
from typing import Any, Iterable, Literal, Mapping, Self, cast, overload, Annotated, AsyncIterable, Callable, Concatenate, ParamSpec, Sequence, Type, TypeVar
from enum import Enum
from uuid import UUID, uuid4
from functools import partial
from inspect import iscoroutinefunction, signature
import json
from pathlib import Path

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Table, ForeignKey, Column, select, String, create_engine, TypeDecorator, Unicode, DateTime
from sqlalchemy.sql import true as sql_true, or_
from sqlalchemy.sql._typing import _ColumnExpressionArgument
from sqlalchemy.orm import relationship, Mapped, mapped_column, sessionmaker, Session, DeclarativeBase, registry, MappedAsDataclass
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy_media import StoreManager, FileSystemStore, File as SqlFile, Attachable
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from pydantic import validator

from algobattle.docker_util import Role as ProgramRole
from algobattle_web.config import SERVER_CONFIG
from algobattle_web.util import BaseSchema, ObjID, PermissionExcpetion


ID = Annotated[UUID, mapped_column(default=uuid4)]

engine = create_engine(SERVER_CONFIG.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autoflush=False, bind=engine)
StoreManager.register("fs", partial(FileSystemStore, SERVER_CONFIG.storage_path, ""), True)


async def get_db() -> AsyncIterable[Session]:
    with SessionLocal() as db, StoreManager(db):
        yield db


P = ParamSpec("P")
R = TypeVar("R")


def autocommit(fn: Callable[P, R]) -> Callable[P, R]:
    """Automatically commits the database transaction."""
    if iscoroutinefunction(fn):
        async def inner_async(*args: P.args, **kwargs: P.kwargs) -> R:
            db = kwargs["db"]
            assert isinstance(db, Session)
            with StoreManager(db):
                res = await fn(*args, **kwargs)
                db.commit()
                return res
        inner_async.__annotations__ = fn.__annotations__
        inner_async.__signature__ = signature(fn)
        return cast(Callable[P, R], inner_async)
    else:
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            db = kwargs["db"]
            assert isinstance(db, Session)
            with StoreManager(db):
                res = fn(*args, **kwargs)
                db.commit()
                return res
        inner.__annotations__ = fn.__annotations__
        inner.__signature__ = signature(fn)
        return inner


class Json(TypeDecorator[Any]):
    impl = Unicode

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return json.loads(value)

class DbFile(SqlFile):
    def attach(
        self,
        attachable: Attachable | UploadFile,
        content_type: str | None = None,
        original_filename: str | None = None,
        extension: str | None = None,
        store_id: str | None = None,
        overwrite: bool = False,
        suppress_pre_process: bool = False,
        suppress_validation: bool = False,
        **kwargs,
    ) -> "DbFile":
        if isinstance(attachable, UploadFile):
            attachable, original_filename = attachable.file, attachable.filename
        return super().attach(
            attachable,
            content_type,   # type: ignore
            original_filename,   # type: ignore
            extension,  # type: ignore
            store_id,   # type: ignore
            overwrite,
            suppress_pre_process,
            suppress_validation,
            **kwargs,
        )

    @classmethod
    def create_from(    # type: ignore
        cls,
        attachable: Attachable | UploadFile,
        content_type: str | None = None,
        original_filename: str | None = None,
        extension: str | None = None,
        store_id: str | None = None,
        overwrite: bool = False,
        suppress_pre_process: bool = False,
        suppress_validation: bool = False,
        **kwargs,
    ) -> "DbFile": ...
    
    def response(self) -> FileResponse:
        """Creates a fastapi FileResponse that serves this file."""
        return FileResponse(Path(SERVER_CONFIG.storage_path) / self.path, filename=self.original_filename, content_disposition_type="inline")

    class Schema(BaseSchema, ABC):
        name: str

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> "DbFile.Schema":
            if isinstance(value, DbFile.Schema):
                return value
            elif isinstance(value, DbFile):
                name = value.original_filename
                return cls(name=name)
            else:
                raise TypeError

DbFile.associate_with(Json)


P = ParamSpec("P")
T = TypeVar("T")
def with_store_manager(func: Callable[Concatenate[Any, Session, P], T]) -> Callable[Concatenate[Any, Session, P], T]:
    def inner(obj, db: Session, *args: P.args, **kwargs: P.kwargs) -> T:
        with StoreManager(db):
            return func(obj, db, *args, **kwargs)
    return inner


@dataclass
class BaseNoID(MappedAsDataclass, DeclarativeBase):
    registry = registry(
        type_annotation_map={
            datetime: DateTime,
            DbFile: Json,
        }
    )

    db: InitVar[Session]

    def __post_init__(self, db: Session) -> None:
        db.add(self)

    class Schema(BaseSchema, ABC):
        pass

    @classmethod
    @property
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    def encode(self) -> dict[str, Any]:
        return jsonable_encoder(self.Schema.from_orm(self))

    @classmethod
    def get_all(cls: Type[T], db: Session) -> Sequence[T]:
        """Get all database entries of this type."""
        return db.scalars(select(cls)).unique().all()

    def as_schema(self) -> Any:
        """Converts the database object into a pydantic schema."""
        return self.Schema.from_orm(self)

    def visible(self, user: "User") -> bool:
        """Checks wether this model is visible to a given user."""
        return True

    @classmethod
    def visible_sql(cls, user: "User") -> _ColumnExpressionArgument[bool]:
        """Emits a sql filter expression that checks whether the model is visible to a given user."""
        return sql_true

    def assert_visible(self, user: "User") -> None:
        """Asserts that this model is visible to a given user."""
        if not self.visible(user):
            raise PermissionExcpetion

    def editable(self, user: "User") -> bool:
        """Checks wether this model is editable by a given user."""
        return True

    @classmethod
    def editable_sql(cls, user: "User") -> _ColumnExpressionArgument[bool]:
        """Emits a sql filter expression that checks whether the model is editable by a given user."""
        return sql_true

    def assert_editable(self, user: "User") -> None:
        """Asserts that this model is editable by a given user."""
        if not self.editable(user):
            raise PermissionExcpetion

    def attach_optional(self, attr: str, file: DbFile | UploadFile | None) -> None:
        """Attaches the file to the attribute."""
        if file is None:
            setattr(self, attr, file)
            return
        current = getattr(self, attr)
        if current is None:
            setattr(self, attr, DbFile.create_from(file))
        else:
            assert isinstance(current, DbFile)
            current.create_from(file)


class Base(BaseNoID, unsafe_hash=True):
    __abstract__ = True
    id: Mapped[ID] = mapped_column(default_factory=uuid4, primary_key=True, init=False)

    class Schema(BaseNoID.Schema, ABC):
        id: ID

    @classmethod
    def get(cls: Type[T], db: Session, identifier: ID) -> T | None:
        """Queries the database for the object with the given id."""
        return db.query(cls).filter(cls.id == identifier).first()   # type: ignore


def encode(col: Iterable[Base]) -> dict[ID, dict[str, Any]]:
    """Encodes a collection of database items into a jsonable container."""
    return jsonable_encoder({el.id: el.encode() for el in col})

team_members = Table(
    "team_members",
    Base.metadata,
    Column("team", ForeignKey("teams.id"), primary_key=True),
    Column("user", ForeignKey("users.id"), primary_key=True),
)


class LoginError(Enum):
    NoToken = 0
    UnregisteredUser = 1
    InvalidToken = 2
    ExpiredToken = 3


class User(Base, unsafe_hash=True):
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    token_id: Mapped[ID] = mapped_column(init=False)
    is_admin: Mapped[bool] = mapped_column(default=False)

    teams: Mapped[list["Team"]] = relationship(secondary=team_members, back_populates="members", lazy="joined", default_factory=list)
    settings: Mapped["UserSettings"] = relationship(back_populates="user", init=False, cascade="all, delete")

    def __post_init__(self, db: Session) -> None:
        UserSettings(db, self.id)
        super().__post_init__(db)

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
    def get(cls, db: Session, identifier: ID | str) -> Self | None:
        """Queries the user db by either the user id or their email."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            return db.scalars(select(cls).filter(cls.email == identifier)).first()

    def cookie(self) -> dict[str, Any]:
        payload = {
            "type": "user",
            "user_id": self.id.hex,
            "token_id": self.token_id.hex,
            "exp": datetime.now() + timedelta(weeks=4),
        }
        return {"key": "user_token", "value": jwt.encode(payload, SERVER_CONFIG.secret_key, SERVER_CONFIG.algorithm)}

    @classmethod
    def decode_token(cls, db: Session, token: str | None) -> Self | None:
        if token is None:
            return
        try:
            payload = jwt.decode(token, SERVER_CONFIG.secret_key, SERVER_CONFIG.algorithm)
            if payload["type"] == "user":
                user_id = UUID(cast(str, payload["user_id"]))
                token_id = UUID(cast(str, payload["token_id"]))
                user = cls.get(db, user_id)
                if user is not None and user.token_id == token_id:
                    return user
        except (JWTError, ExpiredSignatureError, NameError):
            return

    @staticmethod
    def login_token(email: str, lifetime: timedelta = timedelta(hours=1)) -> str:
        payload = {
            "type": "login",
            "email": email,
            "exp": datetime.now() + lifetime,
        }
        return jwt.encode(payload, SERVER_CONFIG.secret_key, SERVER_CONFIG.algorithm)

    @classmethod
    def decode_login_token(cls, db: Session, token: str | None) -> Self | LoginError:
        if token is None:
            return LoginError.NoToken
        try:
            payload = jwt.decode(token, SERVER_CONFIG.secret_key, SERVER_CONFIG.algorithm)
            if payload["type"] == "login":
                user = User.get(db, cast(str, payload["email"]))
                if user is not None:
                    return user
        except ExpiredSignatureError:
            return LoginError.ExpiredToken
        except (JWTError, NameError):
            pass
        return LoginError.InvalidToken


class UserSettings(Base, unsafe_hash=True):
    __tablename__ = "usersettings"  # type: ignore
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    selected_team_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"), default=None)

    user: Mapped[User] = relationship(back_populates="settings", lazy="joined", init=False)
    selected_team: Mapped["Team | None"] = relationship(lazy="joined", init=False)

    class Schema(Base.Schema):
        selected_team: ObjID | None


class Context(Base, unsafe_hash=True):
    name: Mapped[str] = mapped_column(unique=True)

    teams: Mapped[list["Team"]] = relationship(back_populates="context", init=False)

    class Schema(Base.Schema):
        name: str

    @classmethod
    def get(cls, db: Session, identifier: str | ID) -> Self | None:
        """Queries the database for the context with the given id or name."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            return db.scalars(select(cls).filter(cls.name == identifier)).first()


class Team(Base, unsafe_hash=True):
    name: Mapped[str]
    context: Mapped[Context] = relationship(back_populates="teams", uselist=False, lazy="joined")
    context_id: Mapped[ID] = mapped_column(ForeignKey("contexts.id"), init=False)
    members: Mapped[list[User]] = relationship(secondary=team_members, back_populates="teams", lazy="joined", default_factory=list)

    __table_args__ = (UniqueConstraint("name", "context_id"),)

    class Schema(Base.Schema):
        name: str
        context: ObjID
        members: list[ObjID]

    def __str__(self) -> str:
        return self.name

    @overload
    @classmethod
    def get(cls, db: Session, identifier: ID) -> Self | None:
        """Queries the database for the team with the given id."""
        ...

    @overload
    @classmethod
    def get(cls, db: Session, identifier: str, context: Context) -> Self | None:
        """Queries the database for the team with the given name in that context."""
        ...

    @classmethod
    def get(cls, db: Session, identifier: str | ID, context: Context | None = None) -> Self | None:
        """Queries the database for the team with the given id or name and context."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            if context is None:
                raise ValueError("If the team is given by its name, you have to specify a context!")
            return db.query(cls).filter(cls.name == identifier, cls.context_id == context.id).first()


class Config(Base, unsafe_hash=True):
    file: Mapped[DbFile]

    class Schema(Base.Schema):
        name: str


class Problem(Base, unsafe_hash=True):
    name: Mapped[str] = mapped_column(unique=True)
    context: Mapped[Context] = relationship()
    context_id: Mapped[ID] = mapped_column(ForeignKey("contexts.id"), init=False)
    file: Mapped[DbFile]
    config: Mapped[Config] = relationship()
    config_id: Mapped[ID] = mapped_column(ForeignKey("configs.id"), init=False)
    start: Mapped[datetime | None] = mapped_column(default=None)
    end: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[DbFile | None] = mapped_column(default=None)
    short_description: Mapped[str | None] = mapped_column(default=None)
    image: Mapped[DbFile | None] = mapped_column(default=None)
    problem_schema: Mapped[str | None] = mapped_column(default=None)
    solution_schema: Mapped[str | None] = mapped_column(default=None)

    __table_args__ = (UniqueConstraint("name", "context_id"),)

    class Schema(Base.Schema):
        name: str
        context: ObjID
        file: DbFile.Schema
        config: ObjID
        start: datetime | None
        end: datetime | None
        description: DbFile.Schema | None
        short_description: str | None
        image: DbFile.Schema | None

    @classmethod
    def get(cls, db: Session, identifier: ID | str) -> Self | None:
        """Queries the database for the problem with the given id or name."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            return db.query(cls).filter(cls.name == identifier).first()

    def visible(self, user: User) -> bool:
        if user.is_admin or self.start is None:
            return True
        else:
            return self.start <= datetime.now()

    @classmethod
    def visible_sql(cls, user: User) -> _ColumnExpressionArgument[bool]:
        if user.is_admin:
            return sql_true
        else:
            return or_(cls.start.is_(None), cls.start < datetime.now())


class Program(Base, unsafe_hash=True):
    name: Mapped[str]
    team: Mapped[Team] = relationship(lazy="joined")
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), init=False)
    role: Mapped[ProgramRole] = mapped_column(String)
    file: Mapped[DbFile]
    problem: Mapped[Problem] = relationship(lazy="joined")
    problem_id: Mapped[UUID] = mapped_column(ForeignKey("problems.id"), init=False)
    creation_time: Mapped[datetime] = mapped_column(default_factory=datetime.now)
    user_editable: Mapped[bool] = mapped_column(default=True)

    Role = ProgramRole

    class Schema(Base.Schema):
        name: str
        team: ObjID
        role: ProgramRole
        file: DbFile.Schema
        creation_time: datetime
        problem: ObjID
        user_editable: bool


class Documentation(Base, unsafe_hash=True):
    team: Mapped[Team] = relationship(lazy="joined")
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), init=False)
    problem: Mapped[Problem] = relationship(lazy="joined")
    problem_id: Mapped[ID] = mapped_column(ForeignKey("problems.id"), init=False)
    file: Mapped[DbFile]

    __table_args__ = (UniqueConstraint("team_id", "problem_id"),)

    class Schema(Base.Schema):
        team: ObjID
        problem: ObjID
        file: DbFile.Schema

    @overload
    @classmethod
    def get(cls, db: Session, identifier: ID) -> Self | None:
        """Queries the database for the team with the given id."""
        ...

    @overload
    @classmethod
    def get(cls, db: Session, identifier: Team, problem: Problem) -> Self | None:
        """Queries the database for the team with the given name in that context."""
        ...

    @classmethod
    def get(cls, db: Session, identifier: ID | Team, problem: Problem | None = None) -> Self | None:
        """Queries the database for the documentation with the given id or team and problem."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            if problem is None:
                raise TypeError
            return db.query(cls).filter(cls.team_id == identifier.id, cls.problem_id == problem.id).first()


class MatchParticipant(BaseNoID, unsafe_hash=True):
    match: Mapped["ScheduledMatch"] = relationship(back_populates="participants")
    match_id: Mapped[ID] = mapped_column(ForeignKey("scheduledmatches.id"), primary_key=True, init=False)
    team: Mapped[Team] = relationship()
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), primary_key=True, init=False)
    generator_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    generator: Mapped[Program | None] = relationship(foreign_keys=[generator_id])
    solver_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    solver: Mapped[Program | None] = relationship(foreign_keys=[solver_id])

    class Schema(BaseNoID.Schema):
        generator: ObjID | None
        solver: ObjID | None


class ScheduledMatch(Base, unsafe_hash=True):
    __tablename__ = "scheduledmatches"  # type: ignore

    time: Mapped[datetime]
    problem: Mapped[Problem] = relationship()
    problem_id: Mapped[ID] = mapped_column(ForeignKey("problems.id"), init=False)
    config: Mapped[Config | None] = relationship()
    config_id: Mapped[ID | None] = mapped_column(ForeignKey("configs.id"), init=False)
    participants: Mapped[set[MatchParticipant]] = relationship(init=False, default=set, cascade="all, delete")
    name: Mapped[str] = mapped_column(default="")
    points: Mapped[float] = mapped_column(default=0)


    class Schema(Base.Schema):
        name: str
        time: datetime
        problem: ObjID
        config: ObjID | None
        participants: dict[ObjID, MatchParticipant.Schema]
        points: float

        @validator("participants")
        def val_teams(cls, val):
            if not isinstance(val, set):
                raise ValueError
            out = {}
            for v in val:
                if not isinstance(v, MatchParticipant):
                    raise ValueError
                out[v.team_id] = MatchParticipant.Schema.from_orm(val)
            return out


class ResultParticipant(BaseNoID, unsafe_hash=True):
    match: Mapped["MatchResult"] = relationship(back_populates="participants", init=False)
    match_id: Mapped[ID] = mapped_column(ForeignKey("matchresults.id"), primary_key=True, init=False)
    team: Mapped[Team] = relationship()
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), primary_key=True, init=False)
    generator_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    generator: Mapped[Program | None] = relationship(foreign_keys=[generator_id])
    solver_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    solver: Mapped[Program | None] = relationship(foreign_keys=[solver_id])
    points: Mapped[float]

    class Schema(BaseNoID.Schema):
        generator: ObjID
        solver: ObjID
        points: float


class MatchResult(Base, unsafe_hash=True):
    status: Mapped[str]
    time: Mapped[datetime]
    config: Mapped[Config] = relationship()
    config_id: Mapped[ID] = mapped_column(ForeignKey("configs.id"), init=False)
    problem: Mapped[Problem] = relationship()
    problem_id: Mapped[ID] = mapped_column(ForeignKey(Problem.id), init=False)
    participants: Mapped[set[ResultParticipant]] = relationship(default=set)
    logs: Mapped[DbFile | None] = mapped_column(default=None)

    Status = Literal["complete", "failed", "running"]

    class Schema(Base.Schema):
        status: "MatchResult.Status"
        time: datetime
        config: ObjID
        problem: ObjID
        participants: dict[ID, ResultParticipant.Schema]
        logs: DbFile.Schema | None

        @validator("participants")
        def val_teams(cls, val):
            if not isinstance(val, set):
                raise ValueError
            out = {}
            for v in val:
                if not isinstance(v, ResultParticipant):
                    raise ValueError
                out[v.team_id] = ResultParticipant.Schema.from_orm(val)
            return out

    def visible(self, user: User) -> bool:
        return user.is_admin or len(set(user.teams).intersection(p.team for p in self.participants)) != 0
