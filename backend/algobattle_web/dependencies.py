from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie

from algobattle_web.models import User, Session, get_db


def curr_user_maybe(db: Session = Depends(get_db), user_token: str | None = Depends(APIKeyCookie(name="user_token", auto_error=True))) -> User | None:
    return User.decode_token(db, user_token)


def curr_user(user: User | None = Depends(curr_user_maybe)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    else:
        return user


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
