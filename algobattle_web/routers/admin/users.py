"Module specifying the admin user control page."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, get_user
from algobattle_web.templates import templated
from algobattle_web.util import BaseSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    return "admin_users.jinja", {"users": reversed(users)}


class UserAdmin(BaseSchema):
    id: UUID
    make_admin: bool

@router.post("/setadmin")
async def make_admin(*, db: Session = Depends(get_db), user: UserAdmin):
    user_db = get_user(db, user.id)
    if user_db is not None:
        user_db.is_admin = user.make_admin
        db.commit()
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

