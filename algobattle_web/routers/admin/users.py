"Module specifying the admin user control page."
from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User
from algobattle_web.templates import templated

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    return "admin_users.jinja", {"users": reversed(users)}


