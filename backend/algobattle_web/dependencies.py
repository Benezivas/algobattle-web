from typing import AsyncIterable
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from algobattle_web.models import Team, Tournament, User, Session
from algobattle_web.util import SessionLocal


async def get_db() -> AsyncIterable[Session]:
    with SessionLocal() as db:
        try:
            yield db
        except:
            db.rollback()
            raise


def curr_user_maybe(
    db: Session = Depends(get_db), user_token: str | None = Depends(APIKeyHeader(name="X-User-Token"))
) -> User | None:
    return User.decode_token(db, user_token)


def curr_user(user: User | None = Depends(curr_user_maybe)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    else:
        return user


def curr_team(user: User = Depends(curr_user)) -> Team:
    team = user.selected_team
    if team is None:
        raise ValueError("User has not selected a team")
    return team


def curr_tournament(user: User = Depends(curr_user)) -> Tournament:
    if user.current_tournament is None:
        raise HTTPException(400, "User has not selected a team or tournament")
    return user.current_tournament


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
