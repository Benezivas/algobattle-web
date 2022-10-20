"Module specifying the admin user control page."
from __future__ import annotations
from fastapi import APIRouter, Depends, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder

from algobattle_web.database import get_db, Session
from algobattle_web.models.team import Team, Context
from algobattle_web.templates import templated

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    teams = jsonable_encoder(db.query(Team).all())
    contexts = jsonable_encoder(db.query(Context).all()) 
    return "admin_teams.jinja", {"teams": teams, "contexts": contexts}


@router.post("/create_context", response_class=RedirectResponse)
async def context_create(*, db: Session = Depends(get_db), name: str = Form()):
    Context.create(db, name)
    return RedirectResponse("/admin/teams", status_code=status.HTTP_302_FOUND)


@router.post("/create", response_class=RedirectResponse)
async def team_create(db: Session = Depends(get_db), name: str = Form(), context: str = Form()):
    Team.create(db, name, context)
    return RedirectResponse("/admin/teams", status_code=status.HTTP_302_FOUND)
