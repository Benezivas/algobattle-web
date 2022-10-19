"Team model."
from __future__ import annotations
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship, RelationshipProperty as Rel

from algobattle_web.database import Base, Session
from algobattle_web.util import NameTaken

if TYPE_CHECKING:
    from algobattle_web.models.user import User


class Context(Base):
    __tablename__ = "contexts"
    id: UUID = Column(UUIDType, primary_key=True, default=uuid4)   # type: ignore
    name: str = Column(String, unique=True) # type: ignore

    teams: Rel[list[Team]] = relationship("Team", back_populates="context")


def get_context(db: Session, name: str) -> Context | None:
    return db.query(Context).filter(Context.name == name).first()

def create_context(db: Session, name: str) -> Context:
    if get_context(db, name) is not None:
        raise NameTaken(name)
    context = Context(name=name)
    db.add(context)
    db.commit()
    db.refresh(context)
    return context

def update_context(db: Session, context: Context, name: str | None) -> Context:
    if name is not None:
        context.name = name
        db.commit()
    return context

def delete_context(db: Session, context: Context):
    db.delete(context)
    db.commit()


team_members = Table(
    "team_members",
    Base.metadata,
    Column("team", ForeignKey("teams.id"), primary_key=True),
    Column("user", ForeignKey("users.id"), primary_key=True),
)

class Team(Base):
    __tablename__ = "teams"
    id: UUID = Column(UUIDType, primary_key=True, default=uuid4)   # type: ignore
    name: str = Column(String)  # type: ignore
    context_id: UUID = Column(UUIDType, ForeignKey("contexts.id"))  # type: ignore

    context: Rel[Context] = relationship("Context", back_populates="teams", uselist=False)
    members: Rel[list["User"]] = relationship("User", secondary=team_members, back_populates="teams")

    def __str__(self) -> str:
        return self.name


def get_team(db: Session, team: str | UUID, context: str) -> Context | None:
    context = get_context(db, context)
    if context is None:
        raise ValueError
    filter_type = Team.name if isinstance(team, str) else Team.id
    return db.query(Team).filter(filter_type == team and Team.context_id == context.id).first()

def create_team(db: Session, name: str, context: str) -> Team:
    if get_team(db, name, context) is not None:
        raise NameTaken(name)
    context = get_context(db, context)
    if context is None:
        raise ValueError
    team = Team(name=name, context_id=context.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

def update_team(db: Session, team: Team, name: str | None, context: str | Context | None) -> Team:
    if name is not None:
        team.name = name
    if context is not None:
        if isinstance(context, str):
            context = get_context(db, context)
            if context is None:
                raise ValueError
        team.context_id = context.id
    db.commit()
    return context

def delete_team(db: Session, team: Team):
    db.delete(team)
    db.commit()

