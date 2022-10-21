"""Util functions."""
from __future__ import annotations
from datetime import timedelta, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, cast
from dataclasses import dataclass
from pydantic import BaseModel
from fastapi import Depends, Cookie, HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
import tomli
from base64 import b64decode

from algobattle_web.models import User


@dataclass
class ServerConfig:
    secret_key: bytes
    database_url: str
    admin_email: str
    algorithm: str = "HS256"

try:
    with open(Path(__file__).parent / "config.toml", "rb") as f:
        toml_dict = tomli.load(f)["algobattle_web"]
    toml_dict["secret_key"] = b64decode(toml_dict["secret_key"])
    config = ServerConfig(**toml_dict)
except (KeyError, OSError, TypeError):
    raise SystemExit("Badly formatted or missing config.toml!")


engine = create_engine(config.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base: Any = declarative_base()

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    return jwt.encode(payload, config.secret_key, config.algorithm)


def decode_login_token(db: Session, token: str | None) -> User | LoginError:
    if token is None:
        return LoginError.NoToken
    try:
        payload = jwt.decode(token, config.secret_key, config.algorithm)
        if payload["type"] == "login":
            user = User.get(db, cast(str, payload["email"]))
            if user is not None:
                return user
    except ExpiredSignatureError:
        return LoginError.ExpiredToken
    except (JWTError, NameError):
        pass
    return LoginError.InvalidToken


def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True
