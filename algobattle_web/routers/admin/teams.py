"Module specifying the admin user control page."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder

from algobattle_web.database import get_db, Session
from algobattle_web.models.team import Team, create_context, Context
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
    create_context(db, name)
    return RedirectResponse("/admin/teams", status_code=status.HTTP_302_FOUND)