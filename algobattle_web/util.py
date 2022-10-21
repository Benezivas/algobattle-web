"""Util functions."""
from __future__ import annotations
from dataclasses import dataclass
from pydantic import BaseModel
from algobattle_web.database import Session
from fastapi import Depends, Cookie, HTTPException, status
from algobattle_web.database import get_db
from algobattle_web.models import User



def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True


@dataclass
class NameTaken(Exception):
    name: str


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
