from typing import Annotated, AsyncIterable
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import APIKeyHeader

from algobattle_web.models import Team, Tournament, User, Session
from algobattle_web.util import SessionLocal, unwrap


async def get_db() -> AsyncIterable[Session]:
    with SessionLocal() as db:
        try:
            yield db
        except:
            db.rollback()
            raise


Database = Annotated[Session, Depends(get_db)]


def curr_user_maybe(
    db: Session = Depends(get_db), user_token: str | None = Depends(APIKeyHeader(name="X-User-Token"))
) -> User | None:
    return User.decode_token(db, user_token)


CurrUserMaybe = Annotated[User | None, Depends(curr_user_maybe)]


def curr_user(user: User | None = Depends(curr_user_maybe)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    else:
        return user


CurrUser = Annotated[User, Depends(curr_user)]


def curr_team(user: User = Depends(curr_user)) -> Team:
    team = user.settings.selected_team
    if team is None:
        raise ValueError("User has not selected a team")
    return team


CurrTeam = Annotated[Team, Depends(curr_team)]


def curr_tournament(user: User = Depends(curr_user)) -> Tournament:
    if user.settings.selected_team is None:
        raise HTTPException(400, "User has not selected a team or tournament")
    return user.settings.selected_team.tournament


CurrTournament = Annotated[Tournament, Depends(curr_tournament)]


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)


def team_only_if_admin(
    db: Database,
    user: CurrUser,
    team: Annotated[
        UUID | None, Query(description="Can only be set if the user is an admin. Defaults to the user's selected team.")
    ] = None,
) -> Team:
    if user.is_admin and team:
        team_model = Team.get_unwrap(db, team)
    else:
        team_model = unwrap(user.settings.selected_team)
    if not user.is_admin and team_model.id != team:
        raise HTTPException(422, "Non admin users cannot specify a different team than they have selected")
    return team_model


TeamIfAdmin = Annotated[Team, Depends(team_only_if_admin)]
