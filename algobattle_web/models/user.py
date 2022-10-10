"User model and authentication system."
from __future__ import annotations
from datetime import timedelta, datetime
from typing import Any, cast
from uuid import UUID, uuid4
from fastapi import APIRouter, Cookie, HTTPException, Depends, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import Column, String
from sqlalchemy_utils import UUIDType
from sqlalchemy.orm import Session

from algobattle_web.config import SECRET_KEY
from algobattle_web.database import Base, get_db
from algobattle_web.util import OrmModel

router = APIRouter(prefix="/login", tags=["login"])
ALGORITHM = "HS256"


class User(Base):
    __tablename__ = "users"
    id = Column(UUIDType, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    token_id = Column(UUIDType, index=True)


class UserBase(OrmModel):
    email: str
    name: str

class UserCreate(UserBase):
    pass

class UserSchema(UserBase):
    id: UUID
    token_id: UUID

def get_user(db: Session, user: UUID | str) -> User | None:
    """Queries the user db by either the user id or their email."""
    filter_type = User.email if isinstance(user, str) else User.id
    return db.query(User).filter(filter_type == user).first()

def create_user(db: Session, user: UserCreate) -> User:
    """Creates a new user, raises `ValueError` if the email is already in use."""
    if get_user(db, user.email) is not None:
        raise ValueError
    new_user = User(**user.dict(), id=uuid4(), token_id=uuid4())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def user_cookie(user: User) -> dict[str, Any]:
    payload = {
        "type": "user",
        "user_id": user.id.hex,
        "token_id": user.token_id.hex,
        "exp": datetime.now() + timedelta(weeks=4)
    }
    return {"key": "user_token", "value": jwt.encode(payload, SECRET_KEY, ALGORITHM)}


def decode_user_token(db: Session, token: str | None) -> User | None:
    if token is None:
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        if payload["type"] == "user":
            user_id = UUID(cast(str, payload["user_id"]))
            token_id = UUID(cast(str, payload["token_id"]))
            user = get_user(db, user_id)
            if user is not None and user.token_id == token_id:
                return user
    except (JWTError, ExpiredSignatureError, NameError):
        return


def curr_user_maybe(db: Session = Depends(get_db), user_token: str | None = Cookie(default=None)) -> User | None:
    return decode_user_token(db, user_token)


def curr_user(user: User | None = Depends(curr_user_maybe)) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    else:
        return user
