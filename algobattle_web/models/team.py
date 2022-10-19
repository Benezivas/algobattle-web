"Team model."
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import relationship, RelationshipProperty as Rel

from algobattle_web.database import Base, Session

if TYPE_CHECKING:
    from algobattle_web.models.user import User


@dataclass
class ContextNameTaken(Exception):
    name: str


class Context(Base):
    __tablename__ = "contexts"
    id: UUID = Column(UUIDType, primary_key=True, default=uuid4)   # type: ignore
    name: str = Column(String, unique=True) # type: ignore

    teams: Rel[list[Team]] = relationship("Team", back_populates="context")


def get_context(db: Session, name: str) -> Context | None:
    return db.query(Context).filter(Context.name == name).first()

def create_context(db: Session, name: str) -> Context:
    if get_context(db, name) is not None:
        raise ContextNameTaken(name)
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
    id: UUID = Column(UUIDType, primary_key=True)   # type: ignore
    name: str = Column(String)  # type: ignore
    context_id: UUID = Column(UUIDType, ForeignKey("contexts.id"))  # type: ignore

    context: Rel[Context] = relationship("Context", back_populates="teams", uselist=False)
    members: Rel[list["User"]] = relationship("User", secondary=team_members, back_populates="teams")

    def __str__(self) -> str:
        return self.name
