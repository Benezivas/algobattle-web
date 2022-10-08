"Module specifying the login page."
from __future__ import annotations
from datetime import timedelta, datetime
from enum import Enum
from typing import cast
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from algobattle_web.database import get_user, user_exists
from algobattle_web.models.user import User, get_user_maybe, user_cookie

from algobattle_web.templates import templates as t
from algobattle_web.util import send_email
from algobattle_web.secrets import JWT_SECRET

router = APIRouter(prefix="/login", tags=["login"])
ALGORITHM = "HS256"


class LoginError(Enum):
    NoToken = 0
    UnregisteredUser = 1
    InvalidToken = 2
    ExpiredToken = 3


@router.get("", response_class=HTMLResponse)
async def login_get(request: Request, token: str | None = None, user: User | None = Depends(get_user_maybe)):
    res = decode_login_token(token)
    if isinstance(res, User):
        response = RedirectResponse("/")
        response.set_cookie(**user_cookie(res))
        return response
    else:
        return t.TemplateResponse("login.jinja", {
            "request": request,
            "error": res.value,
            "logged_in": str(user) if user is not None else "",
        })


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
