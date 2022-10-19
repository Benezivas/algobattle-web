"Module specifying the admin user control page."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from algobattle_web.database import get_db, Session
from algobattle_web.models.team import Team
from algobattle_web.templates import templated

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    teams = jsonable_encoder(teams)[::-1]
    return "admin_teams.jinja", {"teams": teams}

