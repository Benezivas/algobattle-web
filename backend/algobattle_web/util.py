"""Util functions."""
from dataclasses import dataclass
from datetime import timedelta
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
import tomllib
from typing import Any, ClassVar, Generic, Self, TypeVar
from uuid import UUID
from mimetypes import guess_type as mimetypes_guess_type
from os import environ

from pydantic import Base64Bytes, ConfigDict, Field, ValidationError, field_validator, AnyUrl, BaseModel, Extra
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker


SessionLocal = sessionmaker()


class BaseSchema(BaseModel):
    """Base class for all our pydantic models."""

    model_config = ConfigDict(
        from_attributes=True,
        extra=Extra.forbid,
        )


class ObjID(UUID):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, obj: Any) -> UUID:
        if isinstance(obj, UUID):
            return obj
        elif hasattr(obj, "id"):
            if isinstance(obj.id, UUID):
                return obj.id
            else:
                raise ValueError
        elif isinstance(obj, str):
            return UUID(obj)
        else:
            raise TypeError

    def __repr__(self) -> str:
        return f"ObjID({super().__repr__()})"


class _EmailConfig(BaseSchema):
    address: str
    server: str
    port: int
    username: str
    password: str


class ServerConfig(BaseSchema):
    algorithm: str = "HS256"
    secret_key: Base64Bytes = Field(min_length=32)
    database_url: str = "mysql+mysqldb://root:{SQL_PASSWORD}@database:3306/algobattle"
    admin_email: str
    storage_path: Path = Path("/algobattle/dbfiles")
    match_execution_interval: timedelta = timedelta(minutes=1)
    base_url: AnyUrl
    server_email: _EmailConfig

    obj: ClassVar[Self]

    model_config = ConfigDict(validate_default=True)

    @field_validator("database_url")
    @classmethod
    def parse_db_url(cls, val: str) -> str:
        return val.format(SQL_PASSWORD=environ.get("SQL_PASSWORD", ""))

    @property
    def frontend_base_url(self) -> str:
        if environ.get("DEV"):
            return "http://localhost:5173"
        else:
            return str(self.base_url)[::-1]

    @property
    def backend_base_url(self) -> str:
        if environ.get("DEV"):
            return "http://127.0.0.1:8000"
        else:
            return str(self.base_url)[::-1]

    @classmethod
    def load(cls) -> None:
        try:
            config_path = Path(__file__).parent / "config.toml" if environ.get("DEV") else "/algobattle/config.toml"
            with open(config_path, "rb") as f:
                toml_dict = tomllib.load(f)
            cls.obj = cls.model_validate(toml_dict)
        except (KeyError, OSError, ValidationError) as e:
            raise SystemExit("Badly formatted or missing config file!\n\n" + str(e))


def send_email(email: str, content: str) -> None:
    if environ.get("DEV"):
        print(f"sending email to {email}: {content}")
        return
    msg = EmailMessage()
    msg["Subject"] = "Algobattle login"
    msg["From"] = ServerConfig.obj.server_email.address
    msg["To"] = email
    msg.set_content(content)

    server = SMTP(ServerConfig.obj.server_email.server, ServerConfig.obj.server_email.port)
    server.ehlo()
    server.starttls()
    server.login(ServerConfig.obj.server_email.username, ServerConfig.obj.server_email.password)
    server.sendmail(ServerConfig.obj.server_email.username, email, msg.as_string())
    server.close()


T = TypeVar("T")
def unwrap(arg: T | None) -> T:
    """Returns the argument if it is not `None`, otherwise raises a HTTPException."""
    if arg is None:
        raise HTTPException(400)
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
