"Module specifying the admin user control page."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, create_user, delete_user, get_user, update_user, UserCreate
from algobattle_web.templates import templated
from algobattle_web.util import BaseSchema

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.is_admin).all()
    users = jsonable_encoder(users)[::-1]
    return "admin_users.jinja", {"users": users}


class EditUser(BaseSchema):
    id: UUID
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None


@router.post("/edit", response_model=EditUser)
async def edit_user(*, db: Session = Depends(get_db), edit: EditUser):
    user = get_user(db, edit.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    update_user(db, user, edit.email, edit.name, edit.is_admin)
    return user


@router.post("/create", response_class=RedirectResponse)
async def users_create(*, db: Session = Depends(get_db), name: str = Form(), email: str = Form(), is_admin: bool = Form(default=False)):
    create = UserCreate(email=email, name=name, is_admin=is_admin )
    create_user(db, create)
    return RedirectResponse("/admin/users", status_code=status.HTTP_302_FOUND)


class DeleteUser(BaseSchema):
    id: UUID

@router.post("/delete", response_model=bool)
async def users_delete(*, db: Session = Depends(get_db), user: DeleteUser):
    return delete_user(db, user.id)
