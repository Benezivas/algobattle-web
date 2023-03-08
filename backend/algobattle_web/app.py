from pathlib import Path
from multiprocessing import Process

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run

from algobattle_web.models import Base, SessionLocal, engine, User
from algobattle_web.config import SERVER_CONFIG
from algobattle_web.api import router as api, SchemaRoute
from algobattle_web.pages import router as pages
from algobattle_web.battle import main as battle_main
from algobattle_web.util import PermissionExcpetion, ValueTaken


Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    if User.get(db, SERVER_CONFIG.admin_email) is None:
        User(db, email=SERVER_CONFIG.admin_email, name="Admin", is_admin=True)
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


@app.exception_handler(PermissionExcpetion)
async def perm_err(request: Request, e: PermissionError):
    raise HTTPException(status.HTTP_403_FORBIDDEN)


@app.exception_handler(ValueTaken)
async def val_taken_err(request: Request, e: ValueTaken):
    return JSONResponse(
        status_code=409,
        content=jsonable_encoder({
            "type": "value_taken",
            "field": e.field,
            "value": e.value,
            "object": e.object,
        })
    )

app.include_router(api)
app.include_router(pages)
for route in app.routes:
    if isinstance(route, SchemaRoute):
        route.operation_id = route.name

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


def main():
    """Starts a basic webserver."""
    match_runner = Process(target=battle_main)
    try:
        match_runner.start()
        run("algobattle_web:app")
    finally:
        match_runner.terminate()
