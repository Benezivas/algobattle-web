"Module specifying the home page."
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from algobattle_web.templates import templates as t

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
async def home_get(request: Request):
    return t.TemplateResponse("home.jinja", {"request": request})



