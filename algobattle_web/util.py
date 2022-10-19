"""Util functions."""
from __future__ import annotations
from dataclasses import dataclass
from pydantic import BaseModel



def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True


@dataclass
class NameTaken(Exception):
    name: str
