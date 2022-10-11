"Module specifying the home page."
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from algobattle_web.templates import templated

router = APIRouter(tags=["home"])


@router.get("/", response_class=HTMLResponse)
@templated
async def home_get():
    return "home.jinja"



