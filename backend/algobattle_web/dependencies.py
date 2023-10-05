from dataclasses import dataclass
from typing import Annotated, AsyncIterable, Literal, Self
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
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


Database = Annotated[Session, Depends(get_db)]


def curr_user(
    db: Session = Depends(get_db), user_token: str | None = Depends(APIKeyHeader(name="X-User-Token"))
) -> User | None:
    return User.decode_token(db, user_token)


CurrUser = Annotated[User | None, Depends(curr_user)]


@dataclass
class LoginInfo:
    user: User
    team: Team | Literal["admin"] | None
    tournament: Tournament | None

    @classmethod
    def dependency(cls, user: CurrUser) -> Self:
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        else:
            return cls(user, user.logged_in, user.tournament)


LoggedIn = Annotated[LoginInfo, Depends(LoginInfo.dependency)]


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)


def team_only_if_admin(
    db: Database,
    login: LoggedIn,
    team: Annotated[
        UUID | None, Query(description="Can only be set if the user is an admin. Defaults to the user's selected team.")
    ] = None,
) -> Team:
    match login.team:
        case Team(id=team):
            return Team.get_unwrap(db, team)
        case "admin" if team is not None:
            return Team.get_unwrap(db, team)
        case _:
            raise HTTPException(422, "Non admin users cannot specify a different team than they have selected")


TeamIfAdmin = Annotated[Team, Depends(team_only_if_admin)]
