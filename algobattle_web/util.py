"""Util functions."""
from __future__ import annotations
from pydantic import BaseModel



def send_email(email: str, content: str):
    print(f"sending email to {email}: {content}")


class BaseSchema(BaseModel):
    class Config:
        orm_mode = True

