"Module specifying the regular user pages."
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends, Form, status, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from pydantic import parse_obj_as

from algobattle_web.api import ContextSchema, TeamSchema, UserSchema
from algobattle_web.database import get_db, Session
from algobattle_web.models import Context, Team, User, ValueTaken
from algobattle_web.templates import templated, templates
from algobattle_web.util import curr_user, curr_user_maybe, login_token, decode_login_token, send_email, LoginError

router = APIRouter()


@router.get("/")
@templated
async def home_get():
    return "home.jinja"

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, db: Session = Depends(get_db), token: str | None = None, user: User | None = Depends(curr_user_maybe)):
    res = decode_login_token(db, token)
    if isinstance(res, User):
        response = RedirectResponse("/")
        response.set_cookie(**res.cookie())
        return response
    else:
        return templates.TemplateResponse("login.jinja", {
            "request": request,
            "error": res.value,
            "logged_in": user.name if user is not None else "",
        })


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db), email: str = Form()):
    if User.get(db, email) is not None:
        token = login_token(email)
        send_email(email, f"{request.url_for('login_post')}?token={token}")
        return templates.TemplateResponse("login.jinja", {"request": request, "email_sent": True})
    else:
        return templates.TemplateResponse("login.jinja", {"request": request, "email": email, "error": LoginError.UnregisteredUser.value})

@router.post("/logout")
async def logout_post():
        response = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("user_token")
        return response

@router.get("/user", response_class=HTMLResponse)
@templated
async def user_get():
    return "user.jinja"


@router.post("/user", response_class=HTMLResponse)
@templated
async def user_post(
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    email: str | None = Form(default=None),
    name: str | None = Form(default=None),
):
    context: dict[str, Any] = {}
    try:
        user.update(db, email, name)
    except ValueTaken as e:
        context["error"] = e
    return "user.jinja", context


#*******************************************************************************
#* Admin
#*******************************************************************************

def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

admin = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(check_if_admin)])


@admin.get("/users", response_class=HTMLResponse)
@templated
async def users_get(db: Session = Depends(get_db)):
    users = parse_obj_as(list[UserSchema], db.query(User).order_by(User.is_admin).all())
    users = jsonable_encoder(users)[::-1]
    return "admin_users.jinja", {"users": users}


@admin.get("/teams", response_class=HTMLResponse)
@templated
async def teams_get(db: Session = Depends(get_db)):
    teams = parse_obj_as(list[TeamSchema], db.query(Team).all())
    teams = {t.id: t for t in teams}
    contexts = parse_obj_as(list[ContextSchema], db.query(Context).all())
    contexts = {c.id: c for c in contexts}
    users = parse_obj_as(list[UserSchema], db.query(User).order_by(User.is_admin).all())
    users = {u.id: u for u in users[::-1]}
    return "admin_teams.jinja", {"teams": jsonable_encoder(teams), "contexts": jsonable_encoder(contexts), "users": jsonable_encoder(users)}


#* has to be executed after all route defns
router.include_router(admin)
