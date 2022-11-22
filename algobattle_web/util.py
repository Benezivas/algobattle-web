"""Util functions."""
from __future__ import annotations
from typing import Any, Collection, TypeVar
from fastapi.encoders import jsonable_encoder

from algobattle_web.database import Base, ID


def encode(col: Collection[Base]) -> dict[ID, dict[str, Any]]:
    """Encodes a collection of database items into a jsonable container."""
    return jsonable_encoder({el.id: el.encode() for el in col})


def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")



T = TypeVar("T")
def unwrap(arg: T | None) -> T:
    """Returns the argument if it is not `None`, otherwise raises an exception."""
    if arg is None:
        raise ValueError
    else:
        return arg
