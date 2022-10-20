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

    @classmethod
    def get(cls, db: Session, name: str) -> Context | None:
        return db.query(cls).filter(cls.name == name).first()

    @classmethod
    def create(cls, db: Session, name: str) -> Context:
        if cls.get(db, name) is not None:
            raise NameTaken(name)
        context = Context(name=name)
        db.add(context)
        db.commit()
        db.refresh(context)
        return context

    def update(self, db: Session, name: str | None) -> Context:
        if name is not None:
            self.name = name
            db.commit()
        return self

    def delete(self, db: Session):
        db.delete(self)
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

    @classmethod
    def get(cls, db: Session, team: str | UUID, context: str) -> Team | None:
        context = Context.get(db, context)
        if context is None:
            raise ValueError
        filter_type = cls.name if isinstance(team, str) else Team.id
        return db.query(cls).filter(filter_type == team and cls.context_id == context.id).first()

    @classmethod
    def create(cls, db: Session, name: str, context: str) -> Team:
        if cls.get(db, name, context) is not None:
            raise NameTaken(name)
        context = Context.get(db, context)
        if context is None:
            raise ValueError
        team = cls(name=name, context_id=context.id)
        db.add(team)
        db.commit()
        db.refresh(team)
        return team

    def update(self, db: Session, name: str | None, context: str | Context | None) -> Team:
        if name is not None:
            self.name = name
        if context is not None:
            if isinstance(context, str):
                context = Context.get(db, context)
                if context is None:
                    raise ValueError
            self.context_id = context.id
        db.commit()
        return context

    def delete(self, db: Session):
        db.delete(self)
        db.commit()

