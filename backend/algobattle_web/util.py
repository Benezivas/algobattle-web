"""Util functions."""
from base64 import b64decode
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

from pydantic import AnyUrl, BaseModel, BaseConfig, Extra, validator
from pydantic.color import Color
from pydantic.generics import GenericModel
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker


SessionLocal = sessionmaker()


class BaseSchema(BaseModel):
    class Config(BaseConfig):
        orm_mode = True
        extra = Extra.forbid
        json_encoders = {
            Color: Color.as_hex,
        }


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
    secret_key: bytes
    database_url: str
    admin_email: str
    storage_path: Path
    match_execution_interval: timedelta = timedelta(minutes=5)
    base_url: AnyUrl
    server_email: _EmailConfig

    obj: ClassVar[Self]

    @validator("secret_key")
    def parse_b64(cls, val) -> bytes:
        return b64decode(val)

    @property
    def frontend_base_url(self) -> str:
        if environ.get("DEV", None):
            return "http://localhost:5173"
        else:
            return self.base_url

    @property
    def backend_base_url(self) -> str:
        if environ.get("DEV", None):
            return "http://127.0.0.1:8000"
        else:
            return self.base_url

    @classmethod
    def load(cls) -> None:
        try:
            config_path = Path(environ.get("ALGOBATTLE_CONFIG_PATH", Path(__file__).parent / "config.toml"))
            with open(config_path, "rb") as f:
                toml_dict = tomllib.load(f)
            cls.obj = cls.parse_obj(toml_dict)
        except (KeyError, OSError):
            raise SystemExit("Badly formatted or missing config.toml!")


def send_email(email: str, content: str) -> None:
    if environ.get("DEV", None):
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


class Wrapped(BaseSchema, GenericModel, Generic[T]):
    """Wraps a value in a schema to force json encoding."""
    data: T
