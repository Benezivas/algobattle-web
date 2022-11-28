from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
from sqlalchemy import select
from sqlalchemy_media import StoreManager

from algobattle_web.models import MatchResult, Program, ResultParticipantInfo, Schedule
from algobattle_web.database import DbFile, Session
from algobattle_web.config import STORAGE_PATH

from algobattle.team import TeamInfo
from algobattle.match import MatchInfo
from algobattle.battle import setup_logging

def _extract_to(source: Path, target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with ZipFile(source, "r") as f:
        f.extractall(target)
    return target


def run_match(db: Session, scheduled_match: Schedule):
    logging_path = STORAGE_PATH / "tmp"
    logger = setup_logging(logging_path, verbose_logging=True, silent=False)
    if scheduled_match.config is None:
        config = scheduled_match.problem.config
    else:
        config = scheduled_match.config
    problem_path = _extract_to(STORAGE_PATH / scheduled_match.problem.file.path, STORAGE_PATH / "tmp" / "problem")
        
    participants = []
    team_infos = []
    for participant in scheduled_match.participants:
        if participant.generator.src == "team_spec":
            gen = db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "generator")).unique().first()
        else:
            gen = participant.gen_prog
        assert gen is not None
        gen_path = _extract_to(STORAGE_PATH / gen.file.path, STORAGE_PATH / "tmp" / participant.team.name / "generator")
        
        if participant.solver.src == "team_spec":
            sol = db.scalars(select(Program).where(Program.team_id == participant.team_id, Program.role == "solver")).unique().first()
        else:
            sol = participant.sol_prog
        assert sol is not None
        sol_path = _extract_to(STORAGE_PATH / sol.file.path, STORAGE_PATH / "tmp" / participant.team.name / "solver")

        participants.append(ResultParticipantInfo(participant.team, 0, generator=gen, solver=sol))
        team_infos.append(TeamInfo(participant.team.name, generator=gen_path, solver=sol_path))
    db_result = MatchResult.create(db, schedule=scheduled_match, config=config, status="running", participants=participants)

    with MatchInfo.build(
        problem_path=problem_path,
        config_path = STORAGE_PATH / config.file.path,
        team_infos=team_infos,
        battle_type="iterated",
        rounds=2,
    ) as match_info:
        result = match_info.run_match()
        points = result.calculate_points(scheduled_match.points)
        
        logger.info('#' * 78)
        logger.info(str(result))
        for team, pts in points.items():
            logger.info(f"Team {team} gained {pts:.1f} points.")

        team_table = {team.name: team for team in match_info.teams}
        for participant in db_result.participants:
            participant.points = points[team_table[participant.team.name]]
        db_result.status = "complete"
        for handler in logger.handlers:
            logger.removeHandler(handler)
            handler.close()
        with StoreManager(db), open(logging_path, "rb") as logs:
            db_result.logs = DbFile.create_from(logs)
            db.commit()
