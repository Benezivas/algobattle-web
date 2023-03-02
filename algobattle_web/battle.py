from __future__ import annotations
from datetime import datetime
import logging
from pathlib import Path
from time import sleep
from zipfile import ZipFile
from sqlalchemy import select
from sqlalchemy_media import StoreManager

from algobattle.team import TeamInfo, TeamHandler
from algobattle.match import Match
from algobattle.util import TempDir
from algobattle.problem import Problem
from algobattle.cli import Config
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session, SessionLocal
from algobattle_web.config import SERVER_CONFIG
from algobattle_web.util import unwrap


def _extract_to(source: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(source, "r") as f:
        f.extractall(target)
    return target


def _setup_logging(logging_path: Path, *, verbose: bool = True, silent: bool = False):
    common_logging_level = logging.DEBUG if verbose else logging.INFO
    logging_path.mkdir(exist_ok=True)
    t = datetime.now()
    logging_path = logging_path / f"{t.year:04d}-{t.month:02d}-{t.day:02d}_{t.hour:02d}-{t.minute:02d}-{t.second:02d}.log"

    logging.basicConfig(
            handlers=[logging.FileHandler(logging_path, 'w', 'utf-8')],
            level=common_logging_level,
            format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%H:%M:%S',
            force=True,
        )
    logger = logging.getLogger('algobattle')

    return logger, logging_path


def run_match(db: Session, scheduled_match: ScheduledMatch):
    with TempDir() as folder:
        logger, logging_path = _setup_logging(folder, verbose=True, silent=True)
        if scheduled_match.config is None:
            config = scheduled_match.problem.config
        else:
            config = scheduled_match.config
        problem_path = _extract_to(SERVER_CONFIG.storage_path / scheduled_match.problem.file.path, folder / "problem")
            
        team_info: list[TeamInfo] = []
        paricipants: set[ResultParticipant] = set()
        for participant in scheduled_match.participants:
            if participant.generator is None:
                gen = unwrap(db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "generator")).unique().first())
            else:
                gen = participant.generator
            gen_path = _extract_to(SERVER_CONFIG.storage_path / gen.file.path, folder / participant.team.name / "generator")
            
            if participant.solver is None:
                sol = unwrap(db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "solver")).unique().first())
            else:
                sol = participant.solver
            sol_path = _extract_to(SERVER_CONFIG.storage_path / sol.file.path, folder / participant.team.name / "solver")

            team_info.append(TeamInfo(participant.team.name, gen_path, sol_path))
            paricipants.add(ResultParticipant(db, participant.team, gen, sol, 0))
        db_result = MatchResult(db, "running", datetime.now(), config, scheduled_match.problem, paricipants)
        db.commit()

        config = Config.from_file(Path(config.file.path))
        problem = Problem.import_from_path(problem_path)
        with TeamHandler.build(team_info, problem, config.docker, config.execution.safe_build) as teams:
            result = Match.run(config.match, config.battle_config, problem, teams)
            points = result.calculate_points()
            
            logger.info('#' * 78)
            logger.info(str(result))
            for team, pts in points.items():
                logger.info(f"Team {team} gained {pts:.1f} points.")

            for participant in db_result.participants:
                participant.points = points[participant.team.name]
            db_result.status = "complete"
            logging.shutdown()
            with open(logging_path, "rb") as logs:
                db_result.logs = DbFile.create_from(logs, original_filename=logs.name)
                db.commit()


def run_scheduled_matches():
    time = datetime.now()
    first = time - SERVER_CONFIG.match_execution_interval
    with SessionLocal() as db, StoreManager(db):
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

