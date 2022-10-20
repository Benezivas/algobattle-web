"User model and authentication system."
from __future__ import annotations
from datetime import timedelta, datetime
from typing import Any, Mapping, cast
from uuid import UUID, uuid4
from fastapi import Cookie, HTTPException, Depends, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship, RelationshipProperty as Rel
from sqlalchemy_utils import UUIDType

from algobattle_web.config import SECRET_KEY, ALGORITHM
from algobattle_web.database import get_db, Base, Session
from algobattle_web.models.team import team_members, Team
from algobattle_web.util import NameTaken


class User(Base):
    __tablename__ = "users"
    id: UUID = Column(UUIDType, primary_key=True, default=uuid4)   # type: ignore
    email: str = Column(String, unique=True)    # type: ignore
    name: str = Column(String)  # type: ignore
    token_id: UUID = Column(UUIDType, default=uuid4)   # type: ignore
    is_admin: bool = Column(Boolean, default=False) # type: ignore

    teams: Rel[list[Team]] = relationship("Team", secondary=team_members, back_populates="members")

    def __eq__(self, o: object) -> bool:
        if isinstance(o, User):
            return self.id == o.id
        elif isinstance(o, Mapping):
            if "id" in o:
                if isinstance(o["id"], UUID):
                    return self.id == o["id"]
                elif isinstance(o["id"], str):
                    return str(self.id) == o["id"]
        return NotImplemented

    @classmethod
    def get(cls, db: Session, user: UUID | str) -> User | None:
        """Queries the user db by either the user id or their email."""
        filter_type = cls.email if isinstance(user, str) else cls.id
        return db.query(cls).filter(filter_type == user).first()

    @classmethod
    def create(cls, db: Session, email: str, name: str, is_admin: bool = False) -> User:
        """Creates a new user, raises `EmailTaken` if the email is already in use."""
        if cls.get(db, email) is not None:
            raise NameTaken(email)
        new_user = cls(email=email, name=name, is_admin=is_admin)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user


    def update(self, db: Session, email: str | None = None, name: str | None = None, is_admin: bool | None = None) -> User:
        if email:
            email_user = self.get(db, email)
            if email_user is not None and email_user != self:
                raise NameTaken(email)
            else:
                self.email = email
        if name:
            self.name = name
        if is_admin is not None:
            self.is_admin = is_admin
        db.commit()
        return self


    def delete(self, db: Session):
        db.delete(self)
        db.commit()
        return True

    def cookie(self) -> dict[str, Any]:
        payload = {
            "type": "user",
            "user_id": self.id.hex,
            "token_id": self.token_id.hex,
            "exp": datetime.now() + timedelta(weeks=4)
        }
        return {"key": "user_token", "value": jwt.encode(payload, SECRET_KEY, ALGORITHM)}


    @classmethod
    def decode_token(cls, db: Session, token: str | None) -> User | None:
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


def curr_user_maybe(db: Session = Depends(get_db), user_token: str | None = Cookie(default=None)) -> User | None:
    return User.decode_token(db, user_token)


def curr_user(user: User | None = Depends(curr_user_maybe)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    else:
        return user
