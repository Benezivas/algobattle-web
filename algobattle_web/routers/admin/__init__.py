from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from algobattle_web.models.user import User, curr_user
from algobattle_web.routers.admin.users import router as users

def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(check_if_admin)])

router.include_router(users)
