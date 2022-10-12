"Module specifying the admin user control page."
from __future__ import annotations
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from algobattle_web.templates import templated

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get():
    return "admin_users.jinja"


