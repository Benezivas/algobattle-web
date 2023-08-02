"Database models"
from abc import ABC
from dataclasses import dataclass, InitVar
from datetime import timedelta, datetime
from enum import Enum
from typing import IO, Callable, ClassVar, Iterable, Any
from typing import Any, BinaryIO, Iterable, Literal, Mapping, Self, cast, overload, Annotated, Sequence
from uuid import UUID, uuid4
from pathlib import Path
from urllib.parse import quote as urlencode
from shutil import copyfileobj, copyfile

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import MetaData, Table, ForeignKey, Column, select, DateTime, inspect, String, Text
from sqlalchemy.event import listens_for
from sqlalchemy.sql import true as sql_true, or_, and_
from sqlalchemy.sql._typing import _ColumnExpressionArgument
from sqlalchemy.orm import relationship, Mapped, mapped_column, Session, DeclarativeBase, registry, MappedAsDataclass
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql.base import _NoArg
from fastapi import UploadFile
from fastapi.responses import FileResponse
from pydantic import computed_field, field_validator

from algobattle.docker_util import Role as ProgramRole
from algobattle_web.util import BaseSchema, ObjID, PermissionExcpetion, guess_mimetype, ServerConfig, SessionLocal
from pydantic_extra_types.color import Color


ID = Annotated[UUID, mapped_column(default=uuid4)]
str32 = Annotated[str, mapped_column(String(32))]
str64 = Annotated[str, mapped_column(String(64))]
str128 = Annotated[str, mapped_column(String(128))]
str256 = Annotated[str, mapped_column(String(256))]
strText = Annotated[str, mapped_column(Text)]


class RawBase(MappedAsDataclass, DeclarativeBase):
    registry = registry(
        type_annotation_map={
            datetime: DateTime,
        }
    )

    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })

    def __init_subclass__(cls,
            init: _NoArg | bool = _NoArg.NO_ARG,
            repr: _NoArg | bool = _NoArg.NO_ARG,
            eq: _NoArg | bool = _NoArg.NO_ARG,
            order: _NoArg | bool = _NoArg.NO_ARG,
            unsafe_hash: _NoArg | bool = _NoArg.NO_ARG,
            match_args: _NoArg | bool = _NoArg.NO_ARG,
            kw_only: _NoArg | bool = _NoArg.NO_ARG,
            dataclass_callable: _NoArg | Callable[..., type] = _NoArg.NO_ARG
        ) -> None:
        super().__init_subclass__(init, repr, eq, order, unsafe_hash, match_args, kw_only, dataclass_callable)
        del cls.__dataclass_fields__


class File(RawBase, init=False):
    __tablename__ = "files"

    id: Mapped[ID] = mapped_column(primary_key=True)
    filename: Mapped[str128]
    media_type: Mapped[str32]
    alt_text: Mapped[str256]
    timestamp: Mapped[datetime]

    _move: bool = False
    _file: Path | BinaryIO | None = None

    @overload
    def __init__(self, file: BinaryIO, filename: str, *, media_type: str | None = None, alt_text: str = ""): ...

    @overload
    def __init__(self, file: Self): ...

    @overload
    def __init__(self, file: UploadFile, *, alt_text: str = ""): ...

    @overload
    def __init__(self, file: Path, *, media_type: str | None = None, alt_text: str = "", move: bool): ...

    def __init__(
        self,
        file: BinaryIO | Path | Self | UploadFile,
        filename: str | None = None,
        *,
        media_type: str | None = None,
        alt_text: str = "",
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
            self.filename = file.filename or "UNNAMED_FILE"
            if file.content_type != "application/octet-stream":
                media_type = media_type or file.content_type
        if media_type:
            self.media_type = media_type
        else:
            self.media_type = guess_mimetype(self.filename)
        super().__init__()

    @classmethod
    def maybe(cls, file: UploadFile | None, *, alt_text: str = "") -> Self | None:
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
        return ServerConfig.obj.storage_path / name

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
        if self._file is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(self._file, Path):
                if self._move:
                    self._file.rename(self.path)
                else:
                    copyfile(self._file, self.path)
            else:
                with open(self.path, "wb+") as target:
                    copyfileobj(self._file, target)
            self._file = None
    
    def response(self, content_disposition: Literal["attachment", "inline"] = "attachment") -> FileResponse:
        """Creates a fastapi FileResponse that serves this file."""
        return FileResponse(self.path, filename=self.filename, content_disposition_type=content_disposition, media_type=self.media_type)

    def open(self, mode: str = "rb") -> IO[Any]:
        """Opens the underlying file object."""
        return open(self.path, mode)

    class Schema(BaseSchema, ABC):
        id: ID
        filename: str
        media_type: str
        timestamp: datetime
        alt_text: str

        @computed_field
        @property
        def location(self) -> str:
            return f"{ServerConfig.obj.backend_base_url}/api/files/{urlencode(str(self.id))}"
    Schema.__name__ = "DbFile"


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

    _children: "ClassVar[list[type[BaseNoID]]]" = []

    def __init_subclass__(
            cls,
            init: _NoArg | bool = _NoArg.NO_ARG,
            repr: _NoArg | bool = _NoArg.NO_ARG,
            eq: _NoArg | bool = _NoArg.NO_ARG,
            order: _NoArg | bool = _NoArg.NO_ARG,
            unsafe_hash: _NoArg | bool = _NoArg.NO_ARG,
            match_args: _NoArg | bool = _NoArg.NO_ARG,
            kw_only: _NoArg | bool = _NoArg.NO_ARG
        ) -> None:
        BaseNoID._children.append(cls)
        return super().__init_subclass__(init, repr, eq, order, unsafe_hash, match_args, kw_only)

    class Schema(BaseSchema, ABC):
        pass

    @classmethod
    @property
    def __tablename__(cls):
        return cls.__name__.lower() + "s"

    def encode(self) -> BaseSchema:
        return self.Schema.model_validate(self)

    @classmethod
    def get_all(cls, db: Session) -> Sequence[Self]:
        """Get all database entries of this type."""
        return db.scalars(select(cls)).unique().all()

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
        return self.visible(user)

    @classmethod
    def editable_sql(cls, user: "User") -> _ColumnExpressionArgument[bool]:
        """Emits a sql filter expression that checks whether the model is editable by a given user."""
        return cls.visible_sql(user)

    def assert_editable(self, user: "User") -> None:
        """Asserts that this model is editable by a given user."""
        if not self.editable(user):
            raise PermissionExcpetion


class Base(BaseNoID, unsafe_hash=True):
    __abstract__ = True
    id: Mapped[ID] = mapped_column(default_factory=uuid4, primary_key=True, init=False, autoincrement=False)

    class Schema(BaseNoID.Schema, ABC):
        id: ID


def encode(col: Iterable[Base]) -> dict[ID, Any]:
    """Encodes a collection of database items into a jsonable container."""
    return {el.id: el.encode() for el in col}

team_members = Table(
    "team_members",
    Base.metadata,
    Column("team", ForeignKey("teams.id"), primary_key=True),
    Column("user", ForeignKey("users.id"), primary_key=True),
)


class User(Base, unsafe_hash=True):
    email: Mapped[str128] = mapped_column(unique=True)
    name: Mapped[str32]
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

    def visible(self, user: "User") -> bool:
        return user.is_admin or len(set(user.teams) & set(self.teams)) != 0

    def editable(self, user: "User") -> bool:
        return user.is_admin

    @classmethod
    def get(cls, db: Session, identifier: ID | str) -> Self | None:
        """Queries the user db by either the user id or their email."""
        if isinstance(identifier, UUID):
            return db.get(cls, identifier)
        else:
            return db.scalars(select(cls).filter(cls.email == identifier)).first()

    def cookie(self) -> str:
        payload = {
            "type": "user",
            "user_id": self.id.hex,
            "token_id": self.token_id.hex,
            "exp": datetime.now() + timedelta(weeks=4),
        }
        return jwt.encode(payload, ServerConfig.obj.secret_key, ServerConfig.obj.algorithm)

    @classmethod
    def decode_token(cls, db: Session, token: str | None) -> Self | None:
        if token is None:
            return
        try:
            payload = jwt.decode(token, ServerConfig.obj.secret_key, ServerConfig.obj.algorithm)
            if payload["type"] == "user":
                user_id = UUID(cast(str, payload["user_id"]))
                token_id = UUID(cast(str, payload["token_id"]))
                user = cls.get(db, user_id)
                if user is not None and user.token_id == token_id:
                    return user
        except (JWTError, ExpiredSignatureError, NameError):
            return

    def login_token(self, lifetime: timedelta = timedelta(hours=1)) -> str:
        payload = {
            "type": "login",
            "email": self.email,
            "exp": datetime.now() + lifetime,
        }
        return jwt.encode(payload, ServerConfig.obj.secret_key, ServerConfig.obj.algorithm)

    @classmethod
    def decode_login_token(cls, db: Session, token: str) -> Self:
        try:
            payload = jwt.decode(token, ServerConfig.obj.secret_key, ServerConfig.obj.algorithm)
            if payload["type"] == "login":
                user = User.get(db, cast(str, payload["email"]))
                if user is not None:
                    return user
        except (ExpiredSignatureError, JWTError, NameError):
            pass
        raise ValueError


class UserSettings(Base, unsafe_hash=True):
    __tablename__ = "usersettings"  # type: ignore
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    selected_team_id: Mapped[UUID | None] = mapped_column(ForeignKey("teams.id"), default=None)

    user: Mapped[User] = relationship(back_populates="settings", lazy="joined", init=False)
    selected_team: Mapped["Team | None"] = relationship(lazy="joined", init=False)

    class Schema(Base.Schema):
        selected_team: "Team.Schema | None"


class Tournament(Base, unsafe_hash=True):
    name: Mapped[str32] = mapped_column(unique=True)

    teams: Mapped[list["Team"]] = relationship(back_populates="tournament", init=False)

    class Schema(Base.Schema):
        name: str

    @classmethod
    def get(cls, db: Session, identifier: str | ID) -> Self | None:
        """Queries the database for the tournament with the given id or name."""
        if isinstance(identifier, UUID):
            return db.get(cls, identifier)
        else:
            return db.scalars(select(cls).filter(cls.name == identifier)).first()


class Team(Base, unsafe_hash=True):
    name: Mapped[str32]
    tournament: Mapped[Tournament] = relationship(back_populates="teams", uselist=False, lazy="joined")
    tournament_id: Mapped[ID] = mapped_column(ForeignKey("tournaments.id"), init=False)
    members: Mapped[list[User]] = relationship(secondary=team_members, back_populates="teams", lazy="joined", default_factory=list)

    __table_args__ = (UniqueConstraint("name", "tournament_id"),)

    class Schema(Base.Schema):
        name: str
        tournament: ObjID
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
    def get(cls, db: Session, identifier: str, tournament: Tournament) -> Self | None:
        """Queries the database for the team with the given name in that tournament."""
        ...

    @classmethod
    def get(cls, db: Session, identifier: str | ID, tournament: Tournament | None = None) -> Self | None:
        """Queries the database for the team with the given id or name and tournament."""
        if isinstance(identifier, UUID):
            return db.get(cls, identifier)
        else:
            if tournament is None:
                raise ValueError("If the team is given by its name, you have to specify a tournament!")
            return db.query(cls).filter(cls.name == identifier, cls.tournament_id == tournament.id).first()


class Problem(Base, unsafe_hash=True):
    file_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    config_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    description_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)
    image_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)

    name: Mapped[str64]
    tournament: Mapped[Tournament] = relationship()
    tournament_id: Mapped[ID] = mapped_column(ForeignKey("tournaments.id"), init=False)
    file: Mapped[File] = relationship(foreign_keys=file_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    config: Mapped[File] = relationship(foreign_keys=config_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    start: Mapped[datetime | None] = mapped_column(default=None)
    end: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[File | None] = relationship(default=None, foreign_keys=description_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    short_description: Mapped[str256] = mapped_column(default="")
    image: Mapped[File | None] = relationship(default=None, foreign_keys=image_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    problem_schema: Mapped[strText] = mapped_column(default="")
    solution_schema: Mapped[strText] = mapped_column(default="")
    colour: Mapped[str] = mapped_column(String(7), default="#FFFFFF")

    __table_args__ = (UniqueConstraint("name", "tournament_id"),)

    class Schema(Base.Schema):
        name: str
        tournament: ObjID
        file: File.Schema
        config: File.Schema
        start: datetime | None = None
        end: datetime | None = None
        description: File.Schema | None = None
        short_description: str
        image: File.Schema | None = None
        problem_schema: str | None = None
        solution_schema: str | None = None
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

    def visible(self, user: "User") -> bool:
        return user.is_admin or self.team in user.teams

    def editable(self, user: "User") -> bool:
        return self.visible(user) and (user.is_admin or (self.problem.end is None or self.problem.end >= datetime.now()))

    @classmethod
    def visible_sql(cls, user: "User") -> _ColumnExpressionArgument[bool]:
        if user.is_admin:
            return sql_true
        else:
            return cls.team.in_(user.teams)

    @classmethod
    def editable_sql(cls, user: "User") -> _ColumnExpressionArgument[bool]:
        if user.is_admin:
            return super().editable_sql(user)
        else:
            return and_(super().editable_sql(user), or_(cls.problem.end == None, cls.problem.end >= datetime.now()))


class Program(Base, unsafe_hash=True):
    name: Mapped[str32]
    team: Mapped[Team] = relationship(lazy="joined")
    team_id: Mapped[UUID] = mapped_column(ForeignKey("teams.id"), init=False)
    role: Mapped[ProgramRole]
    file: Mapped[File] = relationship(cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    file_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    problem: Mapped[Problem] = relationship(lazy="joined")
    problem_id: Mapped[UUID] = mapped_column(ForeignKey("problems.id"), init=False)
    creation_time: Mapped[datetime] = mapped_column(default_factory=datetime.now)
    user_editable: Mapped[bool] = mapped_column(default=True)

    @classmethod
    def visible_sql(cls, user: User) -> _ColumnExpressionArgument[bool]:
        if user.is_admin:
            return sql_true
        else:
            return cls.team_id == user.settings.selected_team_id

    class Schema(Base.Schema):
        name: str
        team: ObjID
        role: ProgramRole
        file: File.Schema
        creation_time: datetime
        problem: ObjID
        user_editable: bool


class ScheduledMatch(Base, unsafe_hash=True):
    __tablename__ = "scheduledmatches"  # type: ignore

    time: Mapped[datetime]
    problem: Mapped[Problem] = relationship()
    problem_id: Mapped[ID] = mapped_column(ForeignKey("problems.id"), init=False)
    name: Mapped[str32] = mapped_column(default="")
    points: Mapped[float] = mapped_column(default=100)

    class Schema(Base.Schema):
        name: str
        time: datetime
        problem: ObjID
        points: float


class ResultParticipant(BaseNoID):
    match: Mapped["MatchResult"] = relationship(back_populates="participants", init=False)
    match_id: Mapped[ID] = mapped_column(ForeignKey("matchresults.id"), primary_key=True, init=False)
    team: Mapped[Team] = relationship()
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), primary_key=True, init=False)
    generator_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    generator: Mapped[Program | None] = relationship(foreign_keys=[generator_id])
    solver_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    solver: Mapped[Program | None] = relationship(foreign_keys=[solver_id])
    points: Mapped[float]

    def __hash__(self) -> int:
        return hash(self.team_id)

    class Schema(BaseNoID.Schema):
        generator: ObjID
        solver: ObjID
        points: float


class MatchResult(Base, unsafe_hash=True):
    class Status(Enum):
        complete = "complete"
        failed = "failed"
        running = "running"

    status: Mapped[Status]
    time: Mapped[datetime]
    problem: Mapped[Problem] = relationship()
    problem_id: Mapped[ID] = mapped_column(ForeignKey(Problem.id), init=False)
    participants: Mapped[set[ResultParticipant]] = relationship(default=set)
    config_id: Mapped[ID] = mapped_column(ForeignKey("files.id"), init=False)
    config: Mapped[File | None] = relationship(default=None, foreign_keys=config_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")
    logs_id: Mapped[ID | None] = mapped_column(ForeignKey("files.id"), init=False)
    logs: Mapped[File | None] = relationship(default=None, foreign_keys=logs_id, cascade="all, delete-orphan", single_parent=True, lazy="selectin")


    class Schema(Base.Schema):
        status: "MatchResult.Status"
        time: datetime
        config: File.Schema | None = None
        problem: ObjID
        participants: dict[ID, ResultParticipant.Schema]
        logs: File.Schema | None = None

        @field_validator("participants")
        @classmethod
        def val_teams(cls, val):
            if not isinstance(val, set):
                raise ValueError
            out = {}
            for v in val:
                if not isinstance(v, ResultParticipant):
                    raise ValueError
                out[v.team_id] = ResultParticipant.Schema.model_validate(val)
            return out

    def visible(self, user: User) -> bool:
        return user.is_admin or len(set(user.teams).intersection(p.team for p in self.participants)) != 0

for cls in BaseNoID._children:
    cls.Schema.__name__ = cls.__name__
