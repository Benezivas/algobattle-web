"""Module containing db model's schemas to avoid namespacing issues."""
from abc import ABC
from datetime import datetime
from typing import Annotated
from urllib.parse import quote as urlencode
from uuid import UUID

from pydantic import PlainSerializer, computed_field

from algobattle_web.util import BaseSchema, EnvConfig, MatchStatus, ObjID
from algobattle.util import Role


def naive_localize(date: datetime) -> str:
    """Naively localizes a datetime."""
    return date.astimezone().isoformat()


LocalDatetime = Annotated[datetime, PlainSerializer(naive_localize)]


class Base(BaseSchema, ABC):
    """Base class of database schemas"""

    id: UUID


class DbFile(Base):
    """A file that is stored on disk with metadata in the database."""

    filename: str
    media_type: str
    timestamp: LocalDatetime
    alt_text: str

    @computed_field
    @property
    def location(self) -> str:
        return f"{EnvConfig.get().backend_base_url}/api/files/{urlencode(str(self.id))}"

class Tournament(Base):
    name: str


class Team(Base):
    name: str
    tournament: Tournament
    members: list[ObjID]


class UserSettings(Base):
    selected_team: Team | None
    selected_tournament: Tournament | None


class _User(Base):
    name: str
    email: str
    is_admin: bool


class User(_User):
    teams: list[ObjID]


class UserLogin(_User):
    teams: list[Team]


class Problem(Base):
    name: str
    tournament: Tournament
    file: DbFile
    start: LocalDatetime | None = None
    end: LocalDatetime | None = None
    description: str
    image: DbFile | None = None
    colour: str
    # property is defined on db model to make it have access to the tournament name
    link: str


class Report(Base):
    team: ObjID
    problem: ObjID
    file: DbFile


class Program(Base):
    name: str
    team: ObjID
    role: Role
    file: DbFile
    creation_time: LocalDatetime
    problem: ObjID
    user_editable: bool


class ScheduledMatch(Base):
    name: str
    time: LocalDatetime
    problem: ObjID
    points: float


class ResultParticipant(BaseSchema):
    team_id: UUID
    generator: Program | None = None
    solver: Program | None = None
    points: float


class MatchResult(Base):
    status: MatchStatus
    time: LocalDatetime
    problem: ObjID
    participants: list[ResultParticipant]
    logs: DbFile | None = None
