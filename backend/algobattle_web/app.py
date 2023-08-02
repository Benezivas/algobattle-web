from contextlib import asynccontextmanager
import json
from importlib.resources import as_file, files

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy_utils.functions import database_exists, create_database
from sqlalchemy import create_engine
from alembic.config import Config
from alembic.command import upgrade, stamp
from alembic.migration import MigrationContext

from algobattle_web.models import Base, User
from algobattle_web.api import router as api, SchemaRoute
from algobattle_web.util import PermissionExcpetion, ValueTaken, ServerConfig, SessionLocal


# needs to be top level because of CORSMiddleware
ServerConfig.load()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine(ServerConfig.obj.database_url)
    SessionLocal.configure(bind=engine)

    # this creates the database itself, alembic/sqlalchemy code below creates the tables in it
    if not database_exists(engine.url):
        create_database(engine.url)

    # because python packaged may be installed to eg zipfiles we need make sure all the data is actually on disk
    # however, that isn't easy here since alembic (presumably) expects a bunch of files in a certain structure.
    # this code's invocation of alembic will (probably) just break if you use esoteric install options 🤷‍♀️
    data_files = files("algobattle_web.alembic")
    with (as_file(data_files / "alembic.ini") as alembic_ini):
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("script_location", str(alembic_ini.parent))
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            if context.get_current_revision() is None:
                Base.metadata.create_all(bind=engine)
                stamp(alembic_cfg, "head")
            else:
                upgrade(alembic_cfg, "head")

    # create the default admin user
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
        openapi_version="3.1.0",
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
    allow_origins=(ServerConfig.obj.frontend_base_url,),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_openapi():
    """Prints the openapi.json schema."""
    print(json.dumps(app.openapi()))
