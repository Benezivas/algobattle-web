from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import algobattle_web.database as database
from algobattle_web.models.user import User
from algobattle_web.config import ADMIN_EMAIL
from algobattle_web.routers.api import router as api
from algobattle_web.routers.login import router as login
from algobattle_web.routers.user_pages import router as user_pages
from algobattle_web.routers.admin import router as admin



database.Base.metadata.create_all(bind=database.engine)
with contextmanager(database.get_db)() as db:
    if User.get(db, ADMIN_EMAIL) is None:
        User.create(db, email=ADMIN_EMAIL, name="Admin", is_admin=True)


app = FastAPI()
app.include_router(api)
app.include_router(login)
app.include_router(user_pages)
app.include_router(admin)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
