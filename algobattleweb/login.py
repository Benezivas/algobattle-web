"Module specifying the login page."
from __future__ import annotations
from enum import Enum
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from algobattleweb.templates import templates

router = APIRouter(prefix="/login", tags=["login"])


class LoginError(Enum):
    NoToken = 0
    InvalidToken = 1
    UnregisteredUser = 2


def verify_token(token: str | None) -> str | LoginError:
    if token is None:
        return LoginError.NoToken
    if token == "correct":
        return "yay"
    else:
        return LoginError.InvalidToken

def user_exists(email: str) -> bool:
    return email == "me@e"


@router.get("", response_class=HTMLResponse)
async def login_get(request: Request, token: str | None = None):
    res = verify_token(token)
    if isinstance(res, str):
        return "test"
    else:
        return templates.TemplateResponse("login.jinja", {"request": request, "error": res.value})

@router.post("", response_class=HTMLResponse)
async def login_post(request: Request, email = Form()):
    if user_exists(email):
        return templates.TemplateResponse("login_email_sent.jinja", {"request": request})
    else:
        return templates.TemplateResponse("login.jinja", {"request": request, "email": email, "error": LoginError.UnregisteredUser.value})





