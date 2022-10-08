from __future__ import annotations
from fastapi import FastAPI

from algobattle_web.login import router as login
from algobattle_web.homepage import router as home

app = FastAPI()

app.include_router(login)
app.include_router(home)
