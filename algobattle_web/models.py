"Database models"
from abc import ABC
from dataclasses import dataclass, InitVar
from datetime import timedelta, datetime
from tempfile import SpooledTemporaryFile
from typing import IO, Iterable, Any
from typing import Any, BinaryIO, Iterable, Literal, Mapping, Self, cast, overload, Annotated, AsyncIterable, Sequence
from enum import Enum
from uuid import UUID, uuid4
from pathlib import Path
from urllib.parse import quote as urlencode
from shutil import copyfileobj, copyfile

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Table, ForeignKey, Column, select, String, create_engine, DateTime, inspect
from sqlalchemy.event import listens_for
from sqlalchemy.sql import true as sql_true, or_
from sqlalchemy.sql._typing import _ColumnExpressionArgument
from sqlalchemy.orm import relationship, Mapped, mapped_column, sessionmaker, Session, DeclarativeBase, registry, MappedAsDataclass
from sqlalchemy.schema import UniqueConstraint
from fastapi import UploadFile
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from pydantic import validator
from pydantic.color import Color

from algobattle.docker_util import Role as ProgramRole
from algobattle_web.config import SERVER_CONFIG
from algobattle_web.util import BaseSchema, ObjID, PermissionExcpetion, guess_mimetype


ID = Annotated[UUID, mapped_column(default=uuid4)]

engine = create_engine(SERVER_CONFIG.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autoflush=False, bind=engine)


async def get_db() -> AsyncIterable[Session]:
    with SessionLocal() as db:
        try:
            yield db
        except:
            db.rollback()
            raise


class RawBase(MappedAsDataclass, DeclarativeBase):
    registry = registry(
        type_annotation_map={
            datetime: DateTime,
        }
    )


class File(RawBase, init=False):
    __tablename__ = "files"

    id: Mapped[ID] = mapped_column(primary_key=True)
    filename: Mapped[str]
    media_type: Mapped[str]
    alt_text: Mapped[str | None]
    timestamp: Mapped[datetime]

    @overload
    def __init__(self, file: BinaryIO, filename: str, *, media_type: str | None = None, alt_text: str | None = None): ...

    @overload
    def __init__(self, file: "File"): ...

    @overload
    def __init__(self, file: UploadFile, *, alt_text: str | None = None): ...

    @overload
    def __init__(self, file: Path, *, media_type: str | None = None, alt_text: str | None = None, move: bool): ...

    def __init__(
        self,
        file: "BinaryIO | Path | File | UploadFile",
        filename: str | None = None,
        *,
        media_type: str | None = None,
        alt_text: str | None = None,
        move: bool = False,
    ) -> None:
        self.id = uuid4()

        if isinstance(file, File):
            self._file = file.path
            self._move = False
            self.filename = file.filename
            self.media_type = file.media_type
            self.alt_text = file.alt_text
            self.timestamp = file.timestamp
            super().__init__()
            return

        self.alt_text = alt_text
        self.timestamp = datetime.now()
        if isinstance(file, BinaryIO):
            if filename is None:
                raise TypeError
            self._file = file
            self.filename = filename
        elif isinstance(file, Path):
            self._file = file
            self._move = move
            self.filename = file.name
        else:
            self._file = file.file
            self.filename = file.filename
            if file.content_type != "application/octet-stream":
                media_type = media_type or file.content_type
        if media_type:
            self.media_type = media_type
        else:
            self.media_type = guess_mimetype(self.filename)
        super().__init__()

    @classmethod
    def maybe(cls, file: UploadFile | None, *, alt_text: str | None = None) -> Self | None:
        """Creates a `DbFile` if an `UploadFile` is given, otherwise `None`."""
        if file is None:
            return None
        else:
            return cls(file, alt_text=alt_text)

    @property
    def path(self) -> Path:
        name = str(self.id)
        if self.extension is not None:
            name += f".{self.extension}"
        return SERVER_CONFIG.storage_path / name

    @property
    def extension(self) -> str | None:
        l = self.filename.split(".")
        if l:
            return l[-1]

    def remove(self) -> None:
        """Removes the associated file from disk."""
        self.path.unlink()

    def save(self) -> None:
        """Saves the associated file to disk."""
        if hasattr(self, "_file"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(self._file, (BinaryIO, SpooledTemporaryFile)):
                with open(self.path, "wb+") as target:
                    copyfileobj(self._file, target)
            else:
                if self._move:
                    self._file.rename(self.path)
                else:
                    copyfile(self._file, self.path)
            del self._file
    
    def response(self, content_disposition: Literal["attachment", "inline"] = "attachment") -> FileResponse:
        """Creates a fastapi FileResponse that serves this file."""
        return FileResponse(self.path, filename=self.filename, content_disposition_type=content_disposition, media_type=self.media_type)

    def open(self, mode: str = "rb") -> IO[Any]:
        """Opens the underlying file object."""
        return open(self.path, mode)

    class Schema(BaseSchema, ABC):
        id: ID
        name: str
        location: str
        media_type: str
        timestamp: datetime
        alt_text: str | None = None

        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def validate(cls, value: Any) -> "File.Schema":
            if isinstance(value, File.Schema):
                return value
            elif isinstance(value, File):
                url = f"/api/files/{urlencode(str(value.id))}"
                return cls(
                    id=value.id,
                    name=value.filename,
                    location=url,
                    media_type=value.media_type,
                    alt_text=value.alt_text,
                    timestamp=value.timestamp
                )
            elif isinstance(value, Mapping):
                return cls.parse_obj(value)
            else:
                raise TypeError


@listens_for(File, "after_insert")
def insert_file(_mapper, _connection, target: File):
    inspector = inspect(target)
    assert inspector is not None
    inspector.session.info.setdefault("new_files", []).append(target)


@listens_for(File, "after_delete")
def delete_file(_mapper, _connection, target: File):
    inspector = inspect(target)
    assert inspector is not None
    inspector.session.info.setdefault("deleted_files", []).append(target)


@listens_for(SessionLocal, "after_commit")
def commit_files(db: Session):
    for file in db.info.get("new_files", []):
        assert isinstance(file, File)
        file.save()
    for file in db.info.get("deleted_files", []):
        assert isinstance(file, File)
        file.remove()


@dataclass
class BaseNoID(RawBase):
    __abstract__ = True

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
    def get_all(cls, db: Session) -> Sequence[Self]:
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


class Base(BaseNoID, unsafe_hash=True):
    __abstract__ = True
    id: Mapped[ID] = mapped_column(default_factory=uuid4, primary_key=True, init=False)

    class Schema(BaseNoID.Schema, ABC):
        id: ID


def encode(col: Iterable[Base]) -> dict[ID, Any]:
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
            return db.get(cls, identifier)
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
            return db.get(cls, identifier)
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
            return db.get(cls, identifier)
        else:
            if context is None:
                raise ValueError("If the team is given by its name, you have to specify a context!")
            return db.query(cls).filter(cls.name == identifier, cls.context_id == context.id).first()


class Problem(Base, unsafe_hash=True):
    file_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    config_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    description_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)
    image_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)

    name: Mapped[str]
    context: Mapped[Context] = relationship()
    context_id: Mapped[ID] = mapped_column(ForeignKey("contexts.id"), init=False)
    file: Mapped[File] = relationship(foreign_keys=file_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    config: Mapped[File] = relationship(foreign_keys=config_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    start: Mapped[datetime | None] = mapped_column(default=None)
    end: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[File | None] = relationship(default=None, foreign_keys=description_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    short_description: Mapped[str | None] = mapped_column(default=None)
    image: Mapped[File | None] = relationship(default=None, foreign_keys=image_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    problem_schema: Mapped[str | None] = mapped_column(default=None)
    solution_schema: Mapped[str | None] = mapped_column(default=None)
    colour: Mapped[str] = mapped_column(default=None)

    __table_args__ = (UniqueConstraint("name", "context_id"),)

    class Schema(Base.Schema):
        name: str
        context: ObjID
        file: File.Schema
        config: File.Schema
        start: datetime | None
        end: datetime | None
        description: File.Schema | None
        short_description: str | None
        image: File.Schema | None
        problem_schema: str | None
        solution_schema: str | None
        colour: Color

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


class Documentation(Base, unsafe_hash=True):
    team: Mapped[Team] = relationship(lazy="joined")
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), init=False)
    problem: Mapped[Problem] = relationship(lazy="joined")
    problem_id: Mapped[ID] = mapped_column(ForeignKey("problems.id"), init=False)
    file: Mapped[File] = relationship(cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    file_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)

    __table_args__ = (UniqueConstraint("team_id", "problem_id"),)

    class Schema(Base.Schema):
        team: ObjID
        problem: ObjID
        file: File.Schema


class Program(Base, unsafe_hash=True):
    name: Mapped[str]
    team: Mapped[Team] = relationship(lazy="joined")
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), init=False)
    role: Mapped[ProgramRole] = mapped_column(String)
    file: Mapped[File] = relationship(cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    file_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    problem: Mapped[Problem] = relationship(lazy="joined")
    problem_id: Mapped[UUID] = mapped_column(ForeignKey("problems.id"), init=False)
    creation_time: Mapped[datetime] = mapped_column(default_factory=datetime.now)
    user_editable: Mapped[bool] = mapped_column(default=True)

    Role = ProgramRole

    class Schema(Base.Schema):
        name: str
        team: ObjID
        role: ProgramRole
        file: File.Schema
        creation_time: datetime
        problem: ObjID
        user_editable: bool


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
    config: Mapped[File | None] = relationship(cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    config_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)
    participants: Mapped[set[MatchParticipant]] = relationship(init=False, default=set, cascade="all, delete")
    name: Mapped[str] = mapped_column(default="")
    points: Mapped[float] = mapped_column(default=0)


    class Schema(Base.Schema):
        name: str
        time: datetime
        problem: ObjID
        config: File.Schema | None
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
    problem: Mapped[Problem] = relationship()
    problem_id: Mapped[ID] = mapped_column(ForeignKey(Problem.id), init=False)
    participants: Mapped[set[ResultParticipant]] = relationship(default=set)
    config_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    config: Mapped[File | None] = relationship(default=None, foreign_keys=config_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    logs_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)
    logs: Mapped[File | None] = relationship(default=None, foreign_keys=logs_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")

    Status = Literal["complete", "failed", "running"]

    class Schema(Base.Schema):
        status: "MatchResult.Status"
        time: datetime
        config: File.Schema | None
        problem: ObjID
        participants: dict[ID, ResultParticipant.Schema]
        logs: File.Schema | None

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
