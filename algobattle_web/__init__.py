from __future__ import annotations
from contextlib import contextmanager
from fastapi import FastAPI

import algobattle_web.database as database
from algobattle_web.models.user import UserCreate, create_user, get_user
from algobattle_web.login import router as login
from algobattle_web.home import router as home
from algobattle_web.config import ADMIN_EMAIL



database.Base.metadata.create_all(bind=database.engine)
with contextmanager(database.get_db)() as db:
    if get_user(db, ADMIN_EMAIL) is None:
        create_user(db, UserCreate(email=ADMIN_EMAIL, name="Admin"))


app = FastAPI()
app.include_router(login)
app.include_router(home)


