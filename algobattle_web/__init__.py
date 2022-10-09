from __future__ import annotations
from fastapi import FastAPI

from algobattle_web.login import router as login
from algobattle_web.home import router as home
import algobattle_web.database as database




database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
app.include_router(login)
app.include_router(home)


