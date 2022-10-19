"Module specifying the user page."
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, curr_user, update_user
from algobattle_web.templates import templated
from algobattle_web.util import NameTaken

router = APIRouter(prefix="/user", tags=["user"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get():
    return "user.jinja"


@router.post("", response_class=HTMLResponse)
@templated
async def user_post(
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    email: str | None = Form(default=None),
    name: str | None = Form(default=None),
):
    context: dict[str, Any] = {}
    try:
        update_user(db, user, email, name)
    except NameTaken as e:
        context["error"] = e
    return "user.jinja", context

@router.post("/logout")
async def logout_post():
        response = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("user_token")
        return response
