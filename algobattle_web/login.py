"Module specifying the login page."
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, datetime
from enum import Enum
from uuid import UUID, uuid1
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from algobattle_web.templates import templates as t
from algobattle_web.util import send_email

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




class LoginError(Enum):
    NoToken = 0
    InvalidToken = 1
    UnregisteredUser = 2


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
async def login_post(request: Request, email: str = Form()):
    if user_exists(email):
        token = login_token(email)
        send_email(email, f"{router.url_path_for('')}&token={token}")
        return t.TemplateResponse("login_email_sent.jinja", {"request": request})
    else:
        return t.TemplateResponse("login.jinja", {"request": request, "email": email, "error": LoginError.UnregisteredUser.value})


def login_token(email: str, lifetime: timedelta = timedelta(hours=1)) -> str:
    return f"{email}-{datetime.now() + lifetime}"


def session_token(user: User):
    return user.name


def verify_token(token: str | None) -> str | LoginError:
    if token is None:
        return LoginError.NoToken
    elif token == "correct":
        return "yay"
    else:
        return LoginError.InvalidToken


def user_exists(email: str) -> bool:
    return any(u.email == email for u in db.values())


