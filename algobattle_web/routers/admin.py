"Module specifying the admin pages."
from __future__ import annotations
from fastapi import APIRouter, Depends, status, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder

from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, curr_user
from algobattle_web.models.team import Team, Context
from algobattle_web.templates import templated


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(check_if_admin)])


@router.get("/users", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    users = jsonable_encoder(users)[::-1]
    return "admin_users.jinja", {"users": users}


@router.post("/users/create", response_class=RedirectResponse)
async def users_create(*, db: Session = Depends(get_db), name: str = Form(), email: str = Form(), is_admin: bool = Form(default=False)):
    User.create(db, email, name, is_admin)
    return RedirectResponse("/admin/users", status_code=status.HTTP_302_FOUND)


@router.get("/teams", response_class=HTMLResponse)
@templated
async def teams_get(db: Session = Depends(get_db)):
    teams = jsonable_encoder(db.query(Team).all())
    contexts = jsonable_encoder(db.query(Context).all()) 
    return "admin_teams.jinja", {"teams": teams, "contexts": contexts}


@router.post("/teams/create", response_class=RedirectResponse)
async def team_create(db: Session = Depends(get_db), name: str = Form(), context: str = Form()):
    Team.create(db, name, context)
    return RedirectResponse("/admin/teams", status_code=status.HTTP_302_FOUND)


@router.post("/teams/create_context", response_class=RedirectResponse)
async def context_create(*, db: Session = Depends(get_db), name: str = Form()):
    Context.create(db, name)
    return RedirectResponse("/admin/teams", status_code=status.HTTP_302_FOUND)

