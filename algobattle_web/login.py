"Module specifying the login page."
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta, datetime
from enum import Enum
from typing import cast
from uuid import UUID, uuid1
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from algobattle_web.templates import templates as t
from algobattle_web.util import send_email
from algobattle_web.secrets import JWT_SECRET

router = APIRouter(prefix="/login", tags=["login"])
ALGORITHM = "HS256"


@dataclass
class User:
    email: str
    name: str | None = None
    token_id: UUID | None = None

    def __post_init__(self):
        self.id = uuid1()

db: dict[UUID, User] = {}
def add_user(user: User) -> None:
    db[user.id] = user
add_user(User("me@me"))




class LoginError(Enum):
    NoToken = 0
    UnregisteredUser = 1
    InvalidToken = 2
    ExpiredToken = 3


@router.get("", response_class=HTMLResponse)
async def login_get(request: Request, token: str | None = None):
    res = verify_login_token(token)
    if isinstance(res, str):
        # give session token
        return RedirectResponse("/")
    else:
        return t.TemplateResponse("login.jinja", {"request": request, "error": res.value})


@router.post("", response_class=HTMLResponse)
async def login_post(request: Request, email: str = Form()):
    if user_exists(email):
        token = login_token(email)
        send_email(email, f"{request.url_for('login_post')}?token={token}")
        return t.TemplateResponse("login_email_sent.jinja", {"request": request})
    else:
        return t.TemplateResponse("login.jinja", {"request": request, "email": email, "error": LoginError.UnregisteredUser.value})


def login_token(email: str, lifetime: timedelta = timedelta(hours=1)) -> str:
    payload = {
        "type": "login_token",
        "email": email,
        "exp": datetime.now() + lifetime,
    }
    return jwt.encode(payload, JWT_SECRET, ALGORITHM)


def verify_login_token(token: str | None) -> str | LoginError:
    if token is None:
        return LoginError.NoToken
    try:
        payload = jwt.decode(token, JWT_SECRET, ALGORITHM)
        if payload["type"] == "login_token":
            return cast(str, payload["email"])
        else:
            return LoginError.InvalidToken
    except ExpiredSignatureError:
        return LoginError.ExpiredToken
    except (JWTError, NameError):
        return LoginError.InvalidToken


def user_exists(email: str) -> bool:
    return any(u.email == email for u in db.values())


def session_token(user: User):
    return user.name
