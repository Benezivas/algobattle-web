"Module specifying the login page."
from __future__ import annotations
from typing import Any

from uuid import UUID



db: dict[UUID, Any] = {}
def add_user(user: Any) -> None:
    db[user.id] = user

def user_exists(email: str) -> bool:
    return any(u.email == email for u in db.values())

def get_user(email:str) -> Any | None:
    users = [u for u in db.values() if u.email == email]
    if users:
        return users[0]
    else:
        return None

