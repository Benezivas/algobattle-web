"""Util functions."""
from __future__ import annotations
from datetime import timedelta, datetime
from enum import Enum
from typing import Any, BinaryIO, Collection, cast, overload
from uuid import UUID
from fastapi import Depends, Cookie, HTTPException, status, UploadFile
from fastapi.encoders import jsonable_encoder
from starlette.datastructures import Headers
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from algobattle_web.base_classes import DbBase
from algobattle_web.database import Session, get_db
from algobattle_web.models import User
from algobattle_web.config import SECRET_KEY, ALGORITHM



def encode(col: Collection[DbBase]) -> dict[UUID, dict[str, Any]]:
    """Encodes a collection of database items into a jsonable container."""
    return jsonable_encoder({el.id: el.encode() for el in col})


def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")

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


class LoginError(Enum):
    NoToken = 0
    UnregisteredUser = 1
    InvalidToken = 2
    ExpiredToken = 3

def login_token(email: str, lifetime: timedelta = timedelta(hours=1)) -> str:
    payload = {
        "type": "login",
        "email": email,
        "exp": datetime.now() + lifetime,
    }
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def decode_login_token(db: Session, token: str | None) -> User | LoginError:
    if token is None:
        return LoginError.NoToken
    try:
        payload = jwt.decode(token, SECRET_KEY, ALGORITHM)
        if payload["type"] == "login":
            user = User.get(db, cast(str, payload["email"]))
            if user is not None:
                return user
    except ExpiredSignatureError:
        return LoginError.ExpiredToken
    except (JWTError, NameError):
        pass
    return LoginError.InvalidToken


class File(UploadFile):
    """Common wrapper around different types of file objects to provide easy to use uniform functionality."""

    @overload
    def __init__(self, filename: BinaryIO) -> None:
        """The `filename` is the actual file, not the name!"""
        ...

    @overload
    def __init__(self, filename: str, file: BinaryIO | None = None, content_type: str = "", *, headers: Headers | None = None) -> None:
        ...

    def __init__(self, filename: str | BinaryIO, file: BinaryIO | None = None, content_type: str = "", *, headers: Headers | None = None) -> None:
        if isinstance(filename, BinaryIO):
            return super().__init__(filename.name, filename)
        else:
            return super().__init__(filename, file, content_type=content_type, headers=headers)
