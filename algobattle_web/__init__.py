from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from uvicorn import run

from algobattle_web.models import Base, SessionLocal, engine, User
from algobattle_web.config import ADMIN_EMAIL
from algobattle_web.api import router as api
from algobattle_web.pages import router as pages



Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    if User.get(db, ADMIN_EMAIL) is None:
        User(db, email=ADMIN_EMAIL, name="Admin", is_admin=True)
        db.commit()


app = FastAPI()


@app.exception_handler(RequestValidationError)
async def err_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({
            "detail": e.errors(),
            "body": e.body,
        })
    )


app.include_router(api)
app.include_router(pages)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def main():
    """Starts a basic webserver."""
    run("algobattle_web:app")
