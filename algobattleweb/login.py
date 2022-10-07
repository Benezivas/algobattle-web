"Module specifying user accounts and their interaction."
from __future__ import annotations
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from algobattleweb import templates

router = APIRouter(prefix="/login", tags=["login"])

@router.get("", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.jinja", {"request": request})

@router.post("", response_class=HTMLResponse)
async def login_post(request: Request, username: str = Form(), password: str = Form()):
    return templates.TemplateResponse("login.jinja", {"request": request, "error": password != "yes"})





