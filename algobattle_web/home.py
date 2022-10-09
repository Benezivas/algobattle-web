"Module specifying the home page."
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from algobattle_web.templates import templates as t
from algobattle_web.models.user import User, curr_user

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home_get(request: Request, user: User = Depends(curr_user)):
    return t.TemplateResponse("home.jinja", {"request": request})



