"Module specifying the login page."
from __future__ import annotations
from datetime import timedelta, datetime
from enum import Enum
from typing import cast
from uuid import UUID, uuid4
from fastapi import APIRouter, Request, Form, Cookie, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel, Field

from algobattle_web.templates import templates as t
from algobattle_web.util import send_email
from algobattle_web.secrets import JWT_SECRET

router = APIRouter(prefix="/login", tags=["login"])
ALGORITHM = "HS256"


class User(BaseModel):
    email: str
    name: str | None = None
    id: UUID = Field(default_factory=uuid4)
    token_id: UUID = Field(default_factory=uuid4)

db: dict[UUID, User] = {}
def add_user(user: User) -> None:
    db[user.id] = user
add_user(User(email="me@me"))

def user_exists(email: str) -> bool:
    return any(u.email == email for u in db.values())

def get_user(email:str) -> User | None:
    users = [u for u in db.values() if u.email == email]
    if users:
        return users[0]
    else:
        return None



class LoginError(Enum):
    NoToken = 0
    UnregisteredUser = 1
    InvalidToken = 2
    ExpiredToken = 3


@router.get("", response_class=HTMLResponse)
async def login_get(request: Request, token: str | None = None):
    res = decode_login_token(token)
    if isinstance(res, User):
        response = RedirectResponse("/")
        response.set_cookie("auth_token", auth_token(res))
        return response
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
        "type": "login",
        "email": email,
        "exp": datetime.now() + lifetime,
    }
    return jwt.encode(payload, JWT_SECRET, ALGORITHM)


def decode_login_token(token: str | None) -> User | LoginError:
    if token is None:
        return LoginError.NoToken
    try:
        payload = jwt.decode(token, JWT_SECRET, ALGORITHM)
        if payload["type"] == "login":
            user = get_user(cast(str, payload["email"]))
            if user is not None:
                return user
    except ExpiredSignatureError:
        return LoginError.ExpiredToken
    except (JWTError, NameError):
        pass
    return LoginError.InvalidToken


def auth_token(user: User):
    payload = {
        "type": "auth",
        "user_id": user.id.hex,
        "token_id": user.token_id.hex,
        "exp": datetime.now() + timedelta(weeks=4)
    }
    return jwt.encode(payload, JWT_SECRET, ALGORITHM)


def decode_auth_token(token: str | None) -> User | None:
    if token is None:
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, ALGORITHM)
        if payload["type"] == "auth":
            user_id = UUID(cast(str, payload["user_id"]))
            token_id = UUID(cast(str, payload["token_id"]))
            if user_id in db and db[user_id].token_id == token_id:
                return db[user_id]
    except (JWTError, ExpiredSignatureError, NameError):
        return


def get_curr_user(auth_token: str | None = Cookie(default=None)) -> User:
    user = decode_auth_token(auth_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    else:
        return user

