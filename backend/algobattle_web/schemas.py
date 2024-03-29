"""Module containing db model's schemas to avoid namespacing issues."""
from abc import ABC
from datetime import datetime
from typing import Annotated
from urllib.parse import quote as urlencode
from uuid import UUID

from pydantic import ByteSize, Field, PlainSerializer, computed_field, field_validator

from algobattle_web.util import BaseSchema, EmailConfig, EnvConfig, MatchStatus, ObjID
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
        return f"{EnvConfig.get().base_url}/api/files/{urlencode(str(self.id))}"


class Tournament(Base):
    name: str


class Team(Base):
    name: str
    tournament: Tournament
    members: list[ObjID]


class TeamSettings(Base):
    pass


class ServerSettings(Base):
    user_change_email: bool
    team_change_name: bool
    upload_file_limit: int


class AdminServerSettings(ServerSettings):
    email_config: EmailConfig
    upload_file_limit_text: str = Field(validation_alias="upload_file_limit")

    @field_validator("upload_file_limit_text", mode="before")
    @classmethod
    def _(cls, value: object) -> str:
        if not isinstance(value, int):
            raise ValueError
        return ByteSize(value).human_readable(True)


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


class ExtraPoints(Base):
    time: LocalDatetime
    tag: str
    team: Team
    points: float
    description: str
