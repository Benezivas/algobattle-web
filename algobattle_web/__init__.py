from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import algobattle_web.database as database
from algobattle_web.models import User
from algobattle_web.api import router as api
from algobattle_web.pages import router as pages
from algobattle_web.util import config



database.Base.metadata.create_all(bind=database.engine)
with contextmanager(database.get_db)() as db:
    if User.get(db, config.admin_email) is None:
        User.create(db, email=config.admin_email, name="Admin", is_admin=True)


app = FastAPI()
app.include_router(api)
app.include_router(pages)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
