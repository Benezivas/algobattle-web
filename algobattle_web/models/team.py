"Team model."
from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship, RelationshipProperty as Rel

from algobattle_web.database import Base
if TYPE_CHECKING:
    from algobattle_web.models.user import User


class Context(Base):
    __tablename__ = "contexts"
    id: UUID = Column(UUIDType, primary_key=True)   # type: ignore
    name: str = Column(String, unique=True) # type: ignore

    teams: Rel[list[Team]] = relationship("Team", back_populates="context")


team_members = Table(
    "team_members",
    Base.metadata,
    Column("team", ForeignKey("teams.id"), primary_key=True),
    Column("user", ForeignKey("users.id"), primary_key=True),
)

class Team(Base):
    __tablename__ = "teams"
    id: UUID = Column(UUIDType, primary_key=True)   # type: ignore
    name: str = Column(String)  # type: ignore
    context_id: UUID = Column(UUIDType, ForeignKey("contexts.id"))  # type: ignore

    context: Rel[Context] = relationship("Context", back_populates="teams", uselist=False)
    members: Rel[list["User"]] = relationship("User", secondary=team_members, back_populates="teams")

    def __str__(self) -> str:
        return self.name