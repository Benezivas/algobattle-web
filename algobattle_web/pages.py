"Module specifying the regular user pages."
from typing import Collection
from fastapi import APIRouter, Depends, Form, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func

from algobattle_web.models import (
    ID,
    Base,
    get_db,
    Session,
    Config,
    Context,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
    LoginError,
    encode,
)
from algobattle_web.templates import templated, templates
from algobattle_web.util import send_email, unwrap
from algobattle_web.dependencies import curr_user, curr_user_maybe, check_if_admin

router = APIRouter()
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)])


@router.get("/")
@templated
def home_get():
    return "home.jinja"


@router.get("/login", response_class=HTMLResponse)
def login_get(
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
def login_post(request: Request, db: Session = Depends(get_db), email: str = Form()):
    if User.get(db, email) is not None:
        token = User.login_token(email)
        send_email(email, f"{request.url_for('login_post')}?token={token}")
        return templates.TemplateResponse("login.jinja", {"request": request, "user": None, "email_sent": True})
    else:
        return templates.TemplateResponse(
            "login.jinja", {"request": request, "user": None, "email": email, "error": LoginError.UnregisteredUser.value}
        )


@router.post("/logout")
def logout_post():
    response = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("user_token")
    return response


@router.get("/user", response_class=HTMLResponse)
@templated
def user_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    return "user.jinja", {"teams": encode(user.teams), "settings": user.settings.encode()}


@router.get("/team")
@templated
def team_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    return "team.jinja"


@router.get("/problems")
@templated
def problems_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    if user.is_admin:
        context = user.settings.selected_team.context_id if user.settings.selected_team else None
        problems = db.scalars(select(Problem)).unique().all()
    elif user.settings.selected_team is None:
        return "problems.jinja", {"problems": {}, "contexts": {}, "selected_context": None}
    else:
        context = user.settings.selected_team.context_id
        problems = db.scalars(select(Problem).filter(Problem.visible_sql(user), Problem.context_id == context)).unique().all()
    contexts = db.scalars(select(Context).filter(Context.visible_sql(user))).unique().all()
    return "problems.jinja", {"problems": encode(problems), "contexts": encode(contexts), "selected_context": context}


@router.get("/problems/{context_name}/{problem_name}")
@templated
def problems_details(*, db = Depends(get_db), user = Depends(curr_user), context_name: str, problem_name: str):
    context = unwrap(db.scalars(select(Context).filter(Context.name == context_name)).unique().first())
    problem = unwrap(db.scalars(select(Problem).filter(Problem.name == problem_name, Problem.context_id == context.id)).unique().first())
    problem.assert_visible(user)
    return "problem_detail.jinja", {"problem": problem.encode()}


@admin.get("/problems/create")
@templated
def problem_create(*, db = Depends(get_db)):
    problems = db.scalars(select(Problem)).unique().all()
    encoded = [{"name": f"{p.name} ({p.context.name})", "id": p.id} for p in problems]
    contexts = db.scalars(select(Context)).unique().all()
    return "problem_create.jinja", {"problems": encoded, "contexts": encode(contexts)}

@router.get("/programs")
@templated
def programs_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    params: dict[str, Collection[Base]] = {}
    if user.is_admin:
        params["programs"] = db.query(Program).all()
        params["problems"] = db.query(Problem).all()
        params["teams"] = db.query(Team).all()
    else:
        params["programs"] = db.query(Program).filter(Program.team_id == user.settings.selected_team_id).all()
        params["problems"] = db.query(Problem).filter(Problem.visible_sql(user)).all()
    return "programs.jinja", {k: encode(v) for k, v in params.items()}


@router.get("/schedule")
@templated
def schedule_get(db: Session = Depends(get_db), user: User = Depends(curr_user)):
    schedules = db.scalars(select(ScheduledMatch).join(Problem).where(Problem.visible_sql(user))).unique().all()
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
        "programs": encode(p for p in programs if p is not None),
        "problems": encode(problems),
    }


# *******************************************************************************
# * Admin panel
# *******************************************************************************


@admin.get("/admin/users", response_class=HTMLResponse)
@templated
def users_get(
        db: Session = Depends(get_db),
        name: str | None = None,
        email: str | None = None,
        is_admin: bool | None = None,
        context: ID | None = None,
        team: ID | None = None,
        page: int = 1,
        limit: int = 25,
    ):
    filters = []
    where = []
    if name is not None:
        filters.append(User.name.contains(name, autoescape=True))
    if email is not None:
        filters.append(User.email.contains(email, autoescape=True))
    if is_admin is not None:
        filters.append(User.is_admin == is_admin)
    if context is not None:
        _context = unwrap(db.get(Context, context))
        where.append(User.teams.any(Team.context_id == _context.id))
    if team is not None:
        where.append(User.teams.any(Team.id == team))
    page = max(page - 1, 0)
    users = db.scalars(
        select(User)
        .filter(*filters)
        .where(*where)
        .order_by(User.is_admin.desc())
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    users_count = db.scalar(select(func.count()).select_from(User).filter(*filters)) or 0
    teams = [team for user in users for team in user.teams]
    contexts = db.scalars(select(Context)).unique().all()
    return "admin_users.jinja", {"users": encode(users), "teams": encode(teams), "contexts": encode(contexts), "page": page + 1, "max_page": users_count // limit + 1}


@admin.get("/admin/teams", response_class=HTMLResponse)
@templated
def teams_get(
        db: Session = Depends(get_db),
        name: str | None = None,
        context: ID | None = None,
        page: int = 1,
        limit: int = 25,
    ):
    filters = []
    page = max(page - 1, 0)
    if name is not None:
        filters.append(Team.name.contains(name, autoescape=True))
    if context is not None:
        unwrap(db.get(Context, context))
        filters.append(Team.context_id == context)
    teams = db.scalars(
        select(Team)
        .filter(*filters)
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    team_count = db.scalar(select(func.count()).select_from(Team).filter(*filters)) or 0
    contexts = db.query(Context).all()
    users = [user for team in teams for user in team.members]
    return "admin_teams.jinja", {"teams": encode(teams), "contexts": encode(contexts), "users": encode(users), "page": page + 1, "max_page": team_count // limit + 1}


@admin.get("/admin/contexts")
@templated
def contexts_get(db = Depends(get_db), page: int = 1, limit: int = 25):
    page = max(page - 1, 0)
    contexts = db.scalars(select(Context)).unique().all()
    count = db.scalar(select(func.count()).select_from(Context)) or 0
    return "admin_contexts.jinja", {"contexts": encode(contexts), "page": page + 1, "max_page": count // limit + 1}


# * has to be executed after all route defns
router.include_router(admin)
