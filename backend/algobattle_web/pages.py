"Module specifying the regular user pages."
from typing import Collection

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from algobattle_web.models import (
    Base,
    get_db,
    Session,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
    encode,
)
from algobattle_web.templates import templated
from algobattle_web.dependencies import curr_user

router = APIRouter()


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
