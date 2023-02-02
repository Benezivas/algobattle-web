"Module specifying the regular user pages."
from __future__ import annotations
from typing import Collection
from fastapi import APIRouter, Depends, Form, status, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from algobattle_web.models import (
    Base,
    get_db,
    Session,
    Config,
    Context,
    Documentation,
    MatchResult,
    Problem,
    Program,
    Schedule,
    Team,
    User,
    LoginError,
    encode,
)
from algobattle_web.templates import templated, templates
from algobattle_web.util import send_email
from algobattle_web.dependencies import curr_user, curr_user_maybe

router = APIRouter()


@router.get("/")
@templated
async def home_get():
    return "home.jinja"


@router.get("/login", response_class=HTMLResponse)
async def login_get(
    request: Request, db: Session = Depends(get_db), token: str | None = None, user: User | None = Depends(curr_user_maybe)
):
    res = User.decode_login_token(db, token)
    if isinstance(res, User):
        response = RedirectResponse("/")
        response.set_cookie(**res.cookie())
        return response
    else:
        return templates.TemplateResponse(
            "login.jinja",
            {
                "user": None,
                "request": request,
                "error": res.value,
                "logged_in": user.name if user is not None else "",
            },
        )


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db), email: str = Form()):
    if User.get(db, email) is not None:
        token = User.login_token(email)
        send_email(email, f"{request.url_for('login_post')}?token={token}")
        return templates.TemplateResponse("login.jinja", {"request": request, "user": None, "email_sent": True})
    else:
        return templates.TemplateResponse(
            "login.jinja", {"request": request, "user": None, "email": email, "error": LoginError.UnregisteredUser.value}
        )


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
        problems = db.query(Problem).filter(Problem.visible_sql(user)).all()
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
        params["problems"] = db.query(Problem).filter(Problem.visible_sql(user)).all()
    return "programs.jinja", {k: encode(v) for k, v in params.items()}


@router.get("/documentation")
@templated
def docs_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    if user.settings.selected_team is None:
        raise HTTPException(400)
    problems = db.scalars(select(Problem).where(Problem.visible_sql(user))).all()
    teams = db.scalars(select(Team)).unique().all() if user.is_admin else [user.settings.selected_team]
    docs = db.scalars(select(Documentation)).unique().all()
    if user.is_admin:
        docs_by_team = {
            problem.id: {doc.team.id: doc.encode() for doc in docs if doc.problem == problem} for problem in problems
        }
    else:
        docs_by_team = {doc.problem.id: doc.encode() for doc in docs}
    user_team = user.settings.selected_team
    return "documentation.jinja", {
        "problems": encode(problems),
        "teams": encode(teams),
        "docs": jsonable_encoder(docs_by_team),
        "user_team": user_team.encode(),
    }


@router.get("/schedule")
@templated
def schedule_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    schedules = db.scalars(select(Schedule).join(Problem).where(Problem.visible_sql(user))).unique().all()
    if user.is_admin:
        problems = Problem.get_all(db)
        teams = Team.get_all(db)
        configs = Config.get_all(db)
        progs = Program.get_all(db)
        programs = {
            team.id: {
                "generators": {
                    prog.id: prog.encode() for prog in progs if prog.team == team and prog.role == "generator"
                },
                "solvers": {
                    prog.id: prog.encode() for prog in progs if prog.team == team and prog.role == "solver"
                },
            }
            for team in teams
        }
    else:
        problems = {s.problem for s in schedules}
        teams = {participant.team for sched in schedules for participant in sched.participants}
        configs = {sched.config for sched in schedules if sched.config is not None}
        programs = {}

    return "schedule.jinja", {
        "schedules": encode(schedules),
        "problems": encode(problems),
        "teams": encode(teams),
        "configs": encode(configs),
        "programs": jsonable_encoder(programs),
    }


@router.get("/results")
@templated
def results_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    results = MatchResult.get_all(db)
    if not user.is_admin:
        user_teams = set(user.teams)
        results = [r for r in results if user_teams.intersection(p.team for p in r.participants)]
    teams = {p.team for res in results for p in res.participants}
    programs = {prog for res in results for p in res.participants for prog in (p.generator, p.solver)}
    problems = {res.problem for res in results}

    return "results.jinja", {
        "results": encode(results),
        "teams": encode(teams),
        "programs": encode(programs),
        "problems": encode(problems),
    }


# *******************************************************************************
# * Admin
# *******************************************************************************


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


# * has to be executed after all route defns
router.include_router(admin)
