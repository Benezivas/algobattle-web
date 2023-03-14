"Module specifying the regular user pages."
from typing import Collection

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func

from algobattle_web.models import (
    ID,
    Base,
    get_db,
    Session,
    Context,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
    encode,
)
from algobattle_web.templates import templated
from algobattle_web.util import unwrap
from algobattle_web.dependencies import curr_user, check_if_admin

router = APIRouter()
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)])


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
        programs = {}

    return "schedule.jinja", {
        "schedules": encode(schedules),
        "problems": encode(problems),
        "teams": encode(teams),
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


# * has to be executed after all route defns
router.include_router(admin)
