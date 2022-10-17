"Module specifying the admin user control page."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, get_user, update_user
from algobattle_web.templates import templated
from algobattle_web.util import BaseSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    return "admin_users.jinja", {"users": reversed(jsonable_encoder(users))}


class EditUser(BaseSchema):
    id: UUID
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None


@router.post("/edit", response_model=EditUser)
async def edit_user(*, db: Session = Depends(get_db), edit: EditUser):
    print(edit)
    user = get_user(db, edit.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    update_user(db, user, edit.email, edit.name, edit.is_admin)
    return user
