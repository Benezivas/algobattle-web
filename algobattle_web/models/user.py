"Module specifying the login page."
from __future__ import annotations
from datetime import timedelta, datetime
from typing import Any, cast
from uuid import UUID, uuid4
from fastapi import APIRouter, Cookie, HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel, Field

from algobattle_web.secrets import JWT_SECRET
from algobattle_web.database import db, add_user

router = APIRouter(prefix="/login", tags=["login"])
ALGORITHM = "HS256"


class User(BaseModel):
    email: str
    name: str | None = None
    id: UUID = Field(default_factory=uuid4)
    token_id: UUID = Field(default_factory=uuid4)

add_user(User(email="me@me"))

def user_token(user: User) -> str:
    payload = {
        "type": "user",
        "user_id": user.id.hex,
        "token_id": user.token_id.hex,
        "exp": datetime.now() + timedelta(weeks=4)
    }
    return jwt.encode(payload, JWT_SECRET, ALGORITHM)


def user_cookie(user: User) -> dict[str, Any]:
    return {"key": "user_token", "value": user_token(user)}


def decode_user_token(token: str | None) -> User | None:
    if token is None:
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, ALGORITHM)
        if payload["type"] == "user":
            user_id = UUID(cast(str, payload["user_id"]))
            token_id = UUID(cast(str, payload["token_id"]))
            if user_id in db and db[user_id].token_id == token_id:
                return db[user_id]
    except (JWTError, ExpiredSignatureError, NameError):
        return


def get_user(user_token: str | None = Cookie(default=None)) -> User:
    user = decode_user_token(user_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"},
        )
    else:
        return user
