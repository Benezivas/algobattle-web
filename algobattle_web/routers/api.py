"Module specifying the json api actions."
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from algobattle_web.database import get_db, Session
from algobattle_web.models.user import User, curr_user
from algobattle_web.util import BaseSchema


router = APIRouter(prefix="/api", tags=["api"])


class UserSchema(BaseSchema):
    id: UUID
    name: str
    email: str
    is_admin: bool

class CreateUser(BaseSchema):
    name: str
    email: str
    is_admin: bool = False

class EditUser(BaseSchema):
    id: UUID
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None

class DeleteUser(BaseSchema):
    id: UUID

@router.post("/user/create", response_model=UserSchema)
async def create_user(*, db: Session = Depends(get_db), curr: User = Depends(curr_user), user: CreateUser):
    if not curr.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    return User.create(db, user.email, user.name, user.is_admin)

@router.post("/user/edit", response_model=UserSchema)
async def edit_user(*, db: Session = Depends(get_db), curr: User = Depends(curr_user), edit: EditUser):
    if not (curr.is_admin or edit.id == curr.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    user = User.get(db, edit.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    user.update(db, edit.email, edit.name, edit.is_admin)
    return user

@router.post("/user/delete")
async def delete_user(*, db: Session = Depends(get_db), curr: User = Depends(curr_user), user: DeleteUser):
    if not curr.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    user = User.get(db, user.id)
    if user is None:
        return False
    else:
        user.delete(db)
        return True






