"""Test."""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from algobattleweb.login import router
from algobattleweb import templates

app = FastAPI()

app.include_router(router)

@app.get("/{id}", response_class=HTMLResponse)
async def root(request: Request, id: int):
    return templates.TemplateResponse("login.html", {"request": request, "id": id})
