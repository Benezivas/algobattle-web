"Module specifying the regular user pages."
from __future__ import annotations
from typing import Collection
from fastapi import APIRouter, Depends, Form, status, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from algobattle_web.database import Base, get_db, Session
from algobattle_web.models import Config, Context, Documentation, Problem, Program, Team, User, LoginError
from algobattle_web.templates import templated, templates
from algobattle_web.util import send_email, encode
from algobattle_web.dependencies import curr_user, curr_user_maybe

router = APIRouter()


@router.get("/")
@templated
async def home_get():
    return "home.jinja"

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, db: Session = Depends(get_db), token: str | None = None, user: User | None = Depends(curr_user_maybe)):
    res = User.decode_login_token(db, token)
    if isinstance(res, User):
        response = RedirectResponse("/")
        response.set_cookie(**res.cookie())
        return response
    else:
        return templates.TemplateResponse("login.jinja", {
            "user": None,
            "request": request,
            "error": res.value,
            "logged_in": user.name if user is not None else "",
        })


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db), email: str = Form()):
    if User.get(db, email) is not None:
        token = User.login_token(email)
        send_email(email, f"{request.url_for('login_post')}?token={token}")
        return templates.TemplateResponse("login.jinja", {"request": request, "user": None, "email_sent": True})
    else:
        return templates.TemplateResponse("login.jinja", {"request": request, "user": None, "email": email, "error": LoginError.UnregisteredUser.value})

@router.post("/logout")
async def logout_post():
    response = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("user_token")
    return response

@router.get("/user", response_class=HTMLResponse)
@templated
async def user_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    return "user.jinja", {"teams": encode(user.teams), "settings": user.settings.encode()}

@router.get("/team")
@templated
async def team_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    return "team.jinja"


@router.get("/problems")
@templated
async def problems_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    if user.is_admin:
        problems = db.query(Problem).all()
        configs = db.query(Config).all()
    else:
        problems = db.query(Problem).filter(Problem.visible_to_sql(user)).all()
        configs = {p.config for p in problems}
    return "problems.jinja", {"problems": encode(problems), "configs": encode(configs)}

@router.get("/programs")
@templated
async def programs_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    params: dict[str, Collection[Base]] = {}
    if user.is_admin:
        params["programs"] = db.query(Program).all()
        params["problems"] = db.query(Problem).all()
        params["teams"] = db.query(Team).all()
    else:
        params["programs"] = db.query(Program).filter(Program.team_id == user.settings.selected_team_id).all()
        params["problems"] = db.query(Problem).filter(Problem.visible_to_sql(user)).all()
    return "programs.jinja", {"roles": [r.value for r in Program.Role]} | {k: encode(v) for k, v in params.items()}

@router.get("/documentation")
@templated
def docs_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    if user.settings.selected_team is None:
        raise HTTPException(400)
    problems = db.scalars(select(Problem).where(Problem.visible_to_sql(user))).all()
    teams = db.scalars(select(Team)).unique().all() if user.is_admin else [user.settings.selected_team]
    docs = db.scalars(select(Documentation)).unique().all()
    if user.is_admin:
        docs_by_team = {problem.id: {doc.team.id: doc.encode() for doc in docs if doc.problem == problem} for problem in problems}
    else:
        docs_by_team = {doc.problem.id: doc.encode() for doc in docs}
    user_team = user.settings.selected_team
    return "documentation.jinja", {"problems": encode(problems), "teams": encode(teams), "docs": jsonable_encoder(docs_by_team), "user_team": user_team.encode()}

@router.get("/schedule")
@templated
def schedule_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    return "schedule.jinja"

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
    users = db.query(User).order_by(User.is_admin).all()[::-1]
    teams = db.query(Team).all()
    return "admin_users.jinja", {"users": encode(users), "teams": encode(teams)}


@admin.get("/teams", response_class=HTMLResponse)
@templated
async def teams_get(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    contexts = db.query(Context).all()
    users = db.query(User).order_by(User.is_admin).all()[::-1]
    return "admin_teams.jinja", {"teams": encode(teams), "contexts": encode(contexts), "users": encode(users)}


@admin.get("/configs")
@templated
async def config_get(db: Session = Depends(get_db)):
    configs = db.query(Config).all()
    return "admin_configs.jinja", {"configs": encode(configs)}

#* has to be executed after all route defns
router.include_router(admin)
