"Module specifying the user page."
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import EmailTaken, User, curr_user, update_user
from algobattle_web.templates import templated

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
    except EmailTaken as e:
        context["error"] = e
    return "user.jinja", context
