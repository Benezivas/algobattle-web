"""Util functions."""
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from subprocess import run
import sys
from typing import Annotated, Any, Generic, Self, TypeVar
from uuid import UUID
from mimetypes import guess_type as mimetypes_guess_type
from os import environ
from markdown import markdown

from pydantic import (
    BeforeValidator,
    ConfigDict,
    BaseModel,
)
from fastapi import HTTPException
from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import sessionmaker


@dataclass
class EnvConfig:
    db_url: str
    frontend_base_url: str
    backend_base_url: str
    db_files: Path

    @classmethod
    @lru_cache(maxsize=1)
    def get(cls) -> Self:
        if environ.get("DEV"):
            print(__file__)
            db_path = Path(__file__).parent.parent.joinpath("database.db").resolve()
            print(db_path)
            "database.db"
            return cls(
                db_url=f"sqlite:///{db_path}",
                frontend_base_url="http://localhost:5173",
                backend_base_url="http://127.0.0.1:8000",
                db_files=Path("db_files"),
            )
        else:
            try:
                db_password = environ["ALGOBATTLE_DB_PW"]
            except:
                raise SystemExit(
                    "You need to specify the database password in the `ALGOBATTLE_DB_PW` environment variable"
                )
            try:
                web_url = environ["ALGOBATTLE_BASE_URL"]
            except KeyError:
                raise SystemExit(
                    "You need to specify the base url of your server in the `ALGOBATTLE_BASE_URL` environment variable"
                )
            return cls(
                db_url=f"mysql+mysqldb://root:{db_password}@database:3306/algobattle",
                frontend_base_url=web_url,
                backend_base_url=web_url,
                db_files=Path("/algobattle/dbfiles"),
            )


SessionLocal = sessionmaker()


class BaseSchema(BaseModel):
    """Base class for all our pydantic models."""

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
    )


def model_to_id(obj: object) -> UUID:
    """Validates a pydantic model into a UUID."""
    if isinstance(obj, UUID):
        return obj
    elif hasattr(obj, "id"):
        if isinstance(obj.id, UUID):  # type: ignore
            return obj.id  # type: ignore
        else:
            raise ValueError
    elif isinstance(obj, str):
        return UUID(obj)
    else:
        raise ValueError


ObjID = Annotated[UUID, BeforeValidator(model_to_id)]


class EmailConfig(BaseSchema):
    address: str = ""
    server: str = ""
    port: int = 587
    username: str = ""
    password: str = ""


T = TypeVar("T")


def unwrap(arg: T | None) -> T:
    """Returns the argument if it is not `None`, otherwise raises a HTTPException."""
    if arg is None:
        raise HTTPException(400, detail="Attempted to access a nonexistent resource.")
    else:
        return arg


class AlgobattleError(Exception):
    """Base exception class."""

    pass


@dataclass
class ValueTaken(AlgobattleError):
    """Raised when a uniqueness constrained would be violated."""

    field: str
    value: str
    object: UUID | None = None


@dataclass
class ResourceNeeded(AlgobattleError):
    """Raised to indicate that a value can't be deleted or modified because of references to it."""

    err: str | None = None


class PermissionExcpetion(AlgobattleError):
    """Raised when the user does not have the needed permissions"""

    pass


_extension_map = {
    "md": "text/markdown",
}


def guess_mimetype(info: str | Path) -> str:
    """Guesses a file's mimetype based on it's extension, filename, or path."""
    guess = mimetypes_guess_type(info)[0]
    if guess:
        return guess
    if isinstance(info, Path):
        info = info.name
    return _extension_map.get(info.split(".")[-1], "application/octet-stream")


class Wrapped(BaseSchema, Generic[T]):
    """Wraps a value in a schema to force json encoding."""

    data: T


class MatchStatus(Enum):
    """Possible status of a match."""

    complete = "complete"
    failed = "failed"
    running = "running"


def install_packages(packages: list[str]) -> None:
    """Installs the given packages."""
    if not packages:
        return
    installer = run([sys.executable, "-m", "pip", "install"] + packages, env=environ.copy())
    if installer.returncode:
        raise RuntimeError


def render_text(text: str, mime_type: str = "text/plain") -> str | None:
    """Renders the text as html.

    Accepts text containing plain text, html, or markdown.
    """
    try:
        match mime_type:
            case "text/plain":
                return f"<p>{text}</p>"
            case "text/html":
                return text
            case "text/markdown":
                return markdown(text, extensions=[])
            case _:
                return None
    except Exception:
        return None


M = TypeVar("M", bound=BaseSchema)


class SqlableModel(TypeDecorator, Generic[M]):
    """Stores pydantic objects as JSON in a sql table."""

    impl = JSON
    cache_ok = True

    def __init__(self, source: type[M]):
        self.source = source
        super().__init__()

    def process_bind_param(self, value: M | None, dialect: Dialect) -> dict[str, Any] | None:
        return value.model_dump() if value else None

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> M | None:
        return self.source.model_validate(value) if value else None
