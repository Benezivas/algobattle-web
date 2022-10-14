from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import algobattle_web.database as database
from algobattle_web.models.user import UserCreate, create_user, get_user
from algobattle_web.config import ADMIN_EMAIL
from algobattle_web.routers.login import router as login
from algobattle_web.routers.home import router as home
from algobattle_web.routers.user import router as user
from algobattle_web.routers.admin import router as admin



database.Base.metadata.create_all(bind=database.engine)
with contextmanager(database.get_db)() as db:
    if get_user(db, ADMIN_EMAIL) is None:
        create_user(db, UserCreate(email=ADMIN_EMAIL, name="Admin"), is_admin=True)


app = FastAPI()
app.include_router(login)
app.include_router(home)
app.include_router(user)
app.include_router(admin)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
