from datetime import datetime
from pathlib import Path
from time import sleep
from zipfile import ZipFile
from anyio import run
from sqlalchemy import select

from algobattle.team import TeamInfo
from algobattle.match import Match, BaseConfig
from algobattle.util import TempDir
from algobattle.problem import Problem
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session, SessionLocal
from algobattle_web.config import SERVER_CONFIG
from algobattle_web.util import unwrap


def _extract_to(source: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(source, "r") as f:
        f.extractall(target)
    return target


def run_match(db: Session, scheduled_match: ScheduledMatch):
    with TempDir() as folder:
        if scheduled_match.config is None:
            config_file = scheduled_match.problem.config
        else:
            config_file = scheduled_match.config
        config = BaseConfig.from_file(config_file.path)
        config.teams = {}
        problem = Problem.import_from_path(scheduled_match.problem.file.path)

        paricipants: set[ResultParticipant] = set()
        for participant in scheduled_match.participants:
            if participant.generator is None:
                gen = unwrap(db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "generator")).unique().first())
            else:
                gen = participant.generator
            gen_path = _extract_to(gen.file.path, folder / participant.team.id.hex / "generator")
            
            if participant.solver is None:
                sol = unwrap(db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "solver")).unique().first())
            else:
                sol = participant.solver
            sol_path = _extract_to(sol.file.path, folder / participant.team.id.hex / "solver")

            config.teams[participant.team.name] = TeamInfo(generator=gen_path, solver=sol_path)
            paricipants.add(ResultParticipant(db, participant.team, gen, sol, 0))
        db_result = MatchResult(db, "running", datetime.now(), scheduled_match.problem, paricipants, config_file)
        db.commit()

        result = run(Match.run, config, problem)
        points = result.calculate_points(config.match.points)

        for participant in db_result.participants:
            participant.points = points[participant.team.name]
        db_result.status = "complete"
        with open(folder / "results.json", "x") as f:
            f.write(result.json())
        db_result.logs = File(folder / "result.json", move=True)
        db.commit()


def run_scheduled_matches():
    time = datetime.now()
    first = time - SERVER_CONFIG.match_execution_interval
    with SessionLocal() as db:
        scheduled_matches = db.scalars(select(ScheduledMatch).where(ScheduledMatch.time >= first, ScheduledMatch.time <= time)).unique().all()
        if len(scheduled_matches) == 0:
            return
        # ! Temporary fix, come up with a better solution to this
        if len(scheduled_matches) > 1:
            print("matches are scheduled too close together, aborting their execution!")
            return
        try:
            run_match(db, scheduled_matches[0])
        except BaseException as e:
            print(f"Exception occured when executing match:\n{e}")


def main():
    day = datetime.today()
    next_exec = SERVER_CONFIG.match_execution_interval - (datetime.now() - day) % SERVER_CONFIG.match_execution_interval
    sleep(next_exec.seconds)
    while True:
        run_scheduled_matches()
        sleep(SERVER_CONFIG.match_execution_interval.seconds)

