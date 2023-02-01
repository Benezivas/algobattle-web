"Database models"
#from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Any, BinaryIO, Literal, Mapping, Self, cast, overload
from enum import Enum
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Table, ForeignKey, Column, select, String
from sqlalchemy.sql import true as sql_true, or_
from sqlalchemy.sql._typing import _ColumnExpressionArgument
from sqlalchemy.orm import relationship, Mapped, mapped_column, composite
from fastapi import UploadFile
from uuid import UUID

from algobattle.docker_util import Role as ProgramRole
from algobattle_web.config import SECRET_KEY, ALGORITHM
from algobattle_web.database import Base, Session, DbFile, ID, with_store_manager, BaseNoID
from algobattle_web.base_classes import BaseSchema, ObjID
from algobattle_web.util import unwrap


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

    teams: Mapped[list["Team"]] = relationship(secondary=team_members, back_populates="members", lazy="joined", init=False)
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
        return {"key": "user_token", "value": jwt.encode(payload, SECRET_KEY, ALGORITHM)}

    @classmethod
    def decode_token(cls, db: Session, token: str | None) -> Self | None:
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

    @staticmethod
    def login_token(email: str, lifetime: timedelta = timedelta(hours=1)) -> str:
        payload = {
            "type": "login",
            "email": email,
            "exp": datetime.now() + lifetime,
        }
        return jwt.encode(payload, SECRET_KEY, ALGORITHM)

    @classmethod
    def decode_login_token(cls, db: Session, token: str | None) -> Self | LoginError:
        if token is None:
            return LoginError.NoToken
        try:
            payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
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
    name: Mapped[str] = mapped_column(unique=True)
    context_id: Mapped[ID] = mapped_column(ForeignKey("contexts.id"), init=False)

    context: Mapped[Context] = relationship(back_populates="teams", uselist=False, lazy="joined")
    members: Mapped[list[User]] = relationship(secondary=team_members, back_populates="teams", lazy="joined", init=False)

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
    name: Mapped[str] = mapped_column(unique=True)
    file: Mapped[DbFile]

    class Schema(Base.Schema):
        name: str

    @classmethod
    def get(cls, db: Session, identifier: ID | str) -> Self | None:
        """Queries the database for the config with the given id or name."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            return db.query(cls).filter(cls.name == identifier).first()


class Problem(Base, unsafe_hash=True):
    name: Mapped[str] = mapped_column(unique=True)
    file: Mapped[DbFile]
    config: Mapped[Config] = relationship(uselist=False, lazy="joined")
    config_id: Mapped[ID] = mapped_column(ForeignKey("configs.id"), init=False)
    start: Mapped[datetime | None] = mapped_column(default=None)
    end: Mapped[datetime | None] = mapped_column(default=None)
    description: Mapped[DbFile | None] = mapped_column(default=None)

    class Schema(Base.Schema):
        name: str
        file: DbFile.Schema
        config: ObjID
        start: datetime | None
        end: datetime | None
        description: DbFile.Schema | None

    @classmethod
    def get(cls, db: Session, identifier: ID | str) -> Self | None:
        """Queries the database for the problem with the given id or name."""
        if isinstance(identifier, UUID):
            return super().get(db, identifier)
        else:
            return db.query(cls).filter(cls.name == identifier).first()

    def visible_to(self, user: User) -> bool:
        if user.is_admin or self.start is None:
            return True
        else:
            return self.start <= datetime.now()

    @classmethod
    def visible_to_sql(cls, user: User) -> _ColumnExpressionArgument[bool]:
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

    def __post_init__(self, db: Session) -> None:
        if self.get(db, self.team, self.problem) is not None:
            raise ValueTaken("team/problem")
        return super().__post_init__(db)

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


ProgramSource = Literal["team_spec", "program"]


@dataclass(frozen=True, unsafe_hash=True)
class ProgramSpec:
    src: ProgramSource
    program: ID | None = None

    class Schema(BaseSchema):
        src: ProgramSource
        program: ObjID | None

        def into_obj(self, db: Session) -> "ProgramSpec":
            match self.src:
                case "team_spec":
                    return ProgramSpec("team_spec")
                case "program":
                    prog = unwrap(Program.get(db, unwrap(self.program)))
                    return ProgramSpec("program", prog.id)
                case _:
                    raise ValueError


@dataclass
class ParticipantInfo:
    team: Team
    generator: ProgramSpec
    solver: ProgramSpec

    class Schema(BaseSchema):
        team: ObjID
        generator: ProgramSpec.Schema
        solver: ProgramSpec.Schema

        def into_obj(self, db: Session) -> "ParticipantInfo":
            team = unwrap(Team.get(db, self.team))
            generator = self.generator.into_obj(db)
            solver = self.solver.into_obj(db)
            return ParticipantInfo(team, generator=generator, solver=solver)


class ScheduleParticipant(BaseNoID, unsafe_hash=True):
    schedule_id: Mapped[ID] = mapped_column(ForeignKey("schedules.id"), primary_key=True)
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), primary_key=True, init=False)
    team: Mapped[Team] = relationship(uselist=False)

    gen_src: Mapped[str] = mapped_column(init=False)
    gen_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    gen_prog: Mapped[Program | None] = relationship(foreign_keys=[gen_id], init=False)
    generator: Mapped[ProgramSpec] = composite(ProgramSpec, gen_src, gen_id)

    sol_src: Mapped[str] = mapped_column(init=False)
    sol_id: Mapped[ID | None] = mapped_column(ForeignKey("programs.id"), init=False)
    sol_prog: Mapped[Program | None] = relationship(foreign_keys=[sol_id], init=False)
    solver: Mapped[ProgramSpec] = composite(ProgramSpec, sol_src, sol_id)



class Schedule(Base, unsafe_hash=True):
    time: Mapped[datetime]
    problem: Mapped[Problem] = relationship(uselist=False)
    problem_id: Mapped[ID] = mapped_column(ForeignKey("problems.id"), init=False)
    config: Mapped[Config | None] = relationship(uselist=False)
    config_id: Mapped[ID | None] = mapped_column(ForeignKey("configs.id"), init=False)
    name: Mapped[str] = mapped_column(default="")
    points: Mapped[int] = mapped_column(default=0)

    participants: Mapped[list[ScheduleParticipant]] = relationship(init=False, cascade="all, delete")

    class Schema(Base.Schema):
        name: str
        time: datetime
        problem: ObjID
        config: ObjID | None
        participants: list[ParticipantInfo.Schema]
        points: int

    @classmethod
    def create(
        cls, db: Session, time: datetime, problem: Problem, participants: list[ParticipantInfo], config: Config | None = None, name: str = "", points: int = 0
    ) -> Self:
        if config is None:
            config = problem.config
        schedule = cls(db, time=time, problem=problem, config=config, name=name, points=points)
        for info in participants:
            db.add(ScheduleParticipant(db, schedule_id=schedule.id, team=info.team, generator=info.generator, solver=info.solver))
        return schedule

    #def update(
    #    self,
    #    db: Session,
    #    time: datetime | NoEdit = NoEdit(),
    #    problem: Problem | NoEdit = NoEdit(),
    #    config: Config | None | NoEdit = NoEdit(),
    #    name: str | NoEdit = NoEdit(),
    #    points: int | NoEdit = NoEdit(),
    #    *,
    #    add: list[ParticipantInfo] | None = None,
    #    remove: list[Team] | None = None,
    #):
    #    if add is not None and remove is not None:
    #        raise TypeError
#
    #    if not isinstance(time, NoEdit):
    #        self.time = time
    #    if not isinstance(problem, NoEdit):
    #        self.problem = problem
    #    if not isinstance(config, NoEdit):
    #        self.config = config
    #    if not isinstance(name, NoEdit):
    #        self.name = name
    #    if not isinstance(points, NoEdit):
    #        self.points = points
    #    
    #    if add is not None:
    #        for info in add:
    #            self.participants.append(
    #                ScheduleParticipant(db, schedule_id=self.id, team=info.team, generator=info.generator, solver=info.solver)
    #            )
    #    if remove is not None:
    #        for info in self.participants:
    #            if info.team in remove:
    #                db.delete(info)
    #    db.commit()

@dataclass
class ResultParticipantInfo:
    team: Team
    points: float
    generator: Program
    solver: Program

    class Schema(BaseSchema):
        team: ObjID
        points: float
        generator: ObjID
        solver: ObjID

        def into_obj(self, db: Session) -> "ResultParticipantInfo":
            team = unwrap(Team.get(db, self.team))
            generator = unwrap(Program.get(db, self.generator))
            solver = unwrap(Program.get(db, self.solver))
            return ResultParticipantInfo(team, generator=generator, solver=solver, points=self.points)


class ResultParticipant(BaseNoID, unsafe_hash=True):
    result_id: Mapped[ID] = mapped_column(ForeignKey("matchresults.id"), primary_key=True)
    team_id: Mapped[ID] = mapped_column(ForeignKey("teams.id"), primary_key=True, init=False)
    team: Mapped[Team] = relationship()
    points: Mapped[float]

    gen_id: Mapped[ID] = mapped_column(ForeignKey("programs.id"), init=False)
    generator: Mapped[Program] = relationship(foreign_keys=[gen_id])

    sol_id: Mapped[ID] = mapped_column(ForeignKey("programs.id"), init=False)
    solver: Mapped[Program] = relationship(foreign_keys=[sol_id])


class MatchResult(Base, unsafe_hash=True):
    schedule_id: Mapped[ID] = mapped_column(ForeignKey("schedules.id"), init=False)
    config_id: Mapped[ID] = mapped_column(ForeignKey("configs.id"), init=False)
    status: Mapped[str]
    time: Mapped[datetime]
    problem_id: Mapped[ID] = mapped_column(ForeignKey(Problem.id), init=False)

    participants: Mapped[list[ResultParticipant]] = relationship(init=False)
    schedule: Mapped[Schedule] = relationship()
    config: Mapped[Config] = relationship()
    problem: Mapped[Problem] = relationship()
    logs: Mapped[DbFile | None] = mapped_column(default=None)

    Status = Literal["complete", "failed", "running"]

    class Schema(Base.Schema):
        schedule: ObjID
        logs: DbFile.Schema | None
        config: ObjID
        participants: list[ResultParticipantInfo.Schema]
        status: str
        time: datetime
        problem: ObjID

    @classmethod
    @with_store_manager
    def create(
        cls, db: Session, *, schedule: Schedule, logs: BinaryIO | UploadFile | None = None, config: Config, status: "MatchResult.Status", participants: list[ResultParticipantInfo]
    ) -> Self:
        if logs is not None:
            log_file = DbFile.create_from(logs)
        else:
            log_file = None
        result = cls(db, schedule=schedule, logs=log_file, config=config, status=status, time=datetime.now(), problem=schedule.problem)
        for participant in participants:
            db.add(ResultParticipant(db, result_id=result.id, team=participant.team, points=participant.points, generator=participant.generator, solver=participant.solver))
        return result
