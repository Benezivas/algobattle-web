"""Util functions."""
from __future__ import annotations
from typing import TypeVar


def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")



T = TypeVar("T")
def unwrap(arg: T | None) -> T:
    """Returns the argument if it is not `None`, otherwise raises an exception."""
    if arg is None:
        raise ValueError
    else:
        return arg
