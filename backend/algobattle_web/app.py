from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy_utils.functions import database_exists, create_database

from algobattle_web.models import Base, SessionLocal, engine, User
from algobattle_web.api import router as api, SchemaRoute
from algobattle_web.util import PermissionExcpetion, ValueTaken, ServerConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    ServerConfig.load()
    if not database_exists(engine.url):
        create_database(engine.url)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if User.get(db, ServerConfig.obj.admin_email) is None:
            User(db, email=ServerConfig.obj.admin_email, name="Admin", is_admin=True)
            db.commit()
    yield


app = FastAPI(lifespan=lifespan)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="Algobattle",
        version="0.1.0",
        openapi_version="3.0.0",
        routes=app.routes,
    )
    app.openapi_schema = schema
    return schema
app.openapi = custom_openapi


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
for route in app.routes:
    if isinstance(route, SchemaRoute):
        route.operation_id = route.name


app.add_middleware(
    CORSMiddleware,
    allow_origins=[ServerConfig.obj.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_openapi():
    """Prints the openapi.json schema."""
    print(json.dumps(app.openapi()))
