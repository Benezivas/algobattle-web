from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn import run

from algobattle_web.database import Base, SessionLocal, engine
from algobattle_web.models import User
from algobattle_web.config import ADMIN_EMAIL
from algobattle_web.api import router as api
from algobattle_web.pages import router as pages



Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    if User.get(db, ADMIN_EMAIL) is None:
        User.create(db, email=ADMIN_EMAIL, name="Admin", is_admin=True)


app = FastAPI()
app.include_router(api)
app.include_router(pages)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def main():
    """Starts a basic webserver."""
    run("algobattle_web:app")
