"Module specifying the login page."
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid1
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from algobattle_web.templates import templates as t

router = APIRouter(prefix="/login", tags=["login"])


@dataclass
class User:
    email: str
    name: str | None = None

    def __post_init__(self):
        self.id = uuid1()


db: dict[UUID, User] = {}


def add_user(user: User) -> None:
    db[user.id] = user
add_user(User("me@me"))


def user_exists(email: str) -> bool:
    return any(u.email == email for u in db.values())


class LoginError(Enum):
    NoToken = 0
    InvalidToken = 1
    UnregisteredUser = 2


def verify_token(token: str | None) -> str | LoginError:
    if token is None:
        return LoginError.NoToken
    elif token == "correct":
        return "yay"
    else:
        return LoginError.InvalidToken


@router.get("", response_class=HTMLResponse)
async def login_get(request: Request, token: str | None = None):
    res = verify_token(token)
    if isinstance(res, str):
        # give session token
        # redirect to user page
        return "user page"
    else:
        return t.TemplateResponse("login.jinja", {"request": request, "error": res.value})


@router.post("", response_class=HTMLResponse)
async def login_post(request: Request, email = Form()):
    if user_exists(email):
        # send login token to email
        return t.TemplateResponse("login_email_sent.jinja", {"request": request})
    else:
        return t.TemplateResponse("login.jinja", {"request": request, "email": email, "error": LoginError.UnregisteredUser.value})





