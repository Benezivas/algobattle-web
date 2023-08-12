"""Module containing db model's schemas to avoid namespacing issues."""
from abc import ABC
from datetime import datetime
from urllib.parse import quote as urlencode
from uuid import UUID

from pydantic import computed_field
from pydantic_extra_types.color import Color

from algobattle_web.util import BaseSchema, MatchStatus, ObjID, ServerConfig
from algobattle.docker_util import Role


class Base(BaseSchema, ABC):
    """Base class of database schemas"""

    id: UUID


class DbFile(Base):
    """A file that is stored on disk with metadata in the database."""

    filename: str
    media_type: str
    timestamp: datetime
    alt_text: str

    @computed_field
    @property
    def location(self) -> str:
        return f"{ServerConfig.obj.backend_base_url}/api/files/{urlencode(str(self.id))}"


class User(Base):
    name: str
    email: str
    is_admin: bool
    teams: list[ObjID]


class Tournament(Base):
    name: str


class Team(Base):
    name: str
    tournament: ObjID
    members: list[ObjID]


class UserWithSettings(User):
    selected_team: Team | None
    selected_tournament: Tournament | None
    current_tournament: Tournament | None


class Problem(Base):
    name: str
    tournament: ObjID
    file: DbFile
    config: DbFile
    start: datetime | None = None
    end: datetime | None = None
    description: DbFile | None = None
    short_description: str
    image: DbFile | None = None
    problem_schema: str | None = None
    solution_schema: str | None = None
    colour: Color
    # property is defined on db model to make it have access to the tournament name
    link: str


class Documentation(Base):
    team: ObjID
    problem: ObjID
    file: DbFile


class Program(Base):
    name: str
    team: ObjID
    role: Role
    file: DbFile
    creation_time: datetime
    problem: ObjID
    user_editable: bool


class ScheduledMatch(Base):
    name: str
    time: datetime
    problem: ObjID
    points: float


class ResultParticipant(BaseSchema):
    team_id: UUID
    generator: Program
    solver: Program
    points: float


class MatchResult(Base):
    status: MatchStatus
    time: datetime
    problem: ObjID
    participants: list[ResultParticipant]
    logs: DbFile | None = None
