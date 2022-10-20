"Module specifying the admin user control page."
from __future__ import annotations
from fastapi import APIRouter, Depends, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User
from algobattle_web.templates import templated

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    users = jsonable_encoder(users)[::-1]
    return "admin_users.jinja", {"users": users}


@router.post("/create", response_class=RedirectResponse)
async def users_create(*, db: Session = Depends(get_db), name: str = Form(), email: str = Form(), is_admin: bool = Form(default=False)):
    User.create(db, email, name, is_admin)
    return RedirectResponse("/admin/users", status_code=status.HTTP_302_FOUND)


