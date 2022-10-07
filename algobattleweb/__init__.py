from __future__ import annotations
from fastapi import FastAPI

from algobattleweb.login import router as login_router

app = FastAPI()

app.include_router(login_router)
