from datetime import datetime, timedelta
from os import environ
from time import sleep
from zipfile import ZipFile
from anyio import run
from sqlalchemy import select, create_engine

from algobattle.match import Match, AlgobattleConfig, TeamInfo, ProjectConfig
from algobattle.util import Role, TempDir, ExceptionInfo
from algobattle.battle import ProgramLogConfigTime
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session
from algobattle_web.util import EnvConfig, MatchStatus, install_packages, SessionLocal


def run_match(db: Session, scheduled_match: ScheduledMatch):
    print(f"running match {scheduled_match.name} scheduled at {scheduled_match.time}")
    with TempDir() as folder:
        with ZipFile(scheduled_match.problem.file.path) as zipped:
            zipped.extractall(folder)
        config = AlgobattleConfig.from_file(folder / "algobattle.toml")
        config.teams = {}
        if "project" not in config.model_fields_set:
            config.project = ProjectConfig(
                name_images=False,
                cleanup_images=True,
                error_detail="low",
                log_program_io=ProjectConfig.ProgramOutputConfig(when=ProgramLogConfigTime.never),
            )
        install_packages(config.problem.dependencies)

        participants: dict[str, ResultParticipant] = {}
        excluded_teams = set[str]()
        for team in scheduled_match.problem.tournament.teams:
            gen = (
                db.scalars(
                    select(Program)
                    .where(
                        Program.team_id == team.id,
                        Program.problem_id == scheduled_match.problem_id,
                        Program.role == Role.generator,
                    )
                    .order_by(Program.creation_time.desc())
                    .limit(1)
                )
                .unique()
                .first()
            )
            sol = (
                db.scalars(
                    select(Program)
                    .where(
                        Program.team_id == team.id,
                        Program.problem_id == scheduled_match.problem_id,
                        Program.role == Role.solver,
                    )
                    .order_by(Program.creation_time.desc())
                    .limit(1)
                )
                .unique()
                .first()
            )

            if gen and sol:
                config.teams[team.name] = TeamInfo(generator=gen.file.path, solver=sol.file.path)
            else:
                excluded_teams.add(team.name)
            participants[team.name] = ResultParticipant(team, gen, sol, 0)
        now = datetime.now()
        db_result = MatchResult(
            MatchStatus.running,
            now - timedelta(seconds=now.second, microseconds=now.microsecond),
            scheduled_match.problem,
            set(participants.values()),
        )
        db.add(db_result)
        db.commit()

        try:
            result = run(Match().run, config)
        except Exception as e:
            db_result.status = MatchStatus.failed
            folder.joinpath("result.json").write_text(ExceptionInfo.from_exception(e).model_dump_json())
            db_result.logs = File.from_file(folder / "result.json", action="move")
        else:
            result.excluded_teams |= {
                team: ExceptionInfo(type="RuntimeError", message="missing program") for team in excluded_teams
            }
            points = result.calculate_points(scheduled_match.points)

            for orig_name, team in participants.items():
                team.points = points.get(orig_name, 0)
            db_result.status = MatchStatus.complete
            folder.joinpath("result.json").write_text(result.format(error_detail=config.project.error_detail))
            db_result.logs = File.from_file(folder / "result.json", action="move")
        finally:
            db.delete(scheduled_match)
            db.commit()


def main():
    engine = create_engine(EnvConfig.get().db_url)
    SessionLocal.configure(bind=engine)
    last_check = datetime.now()
    while True:
        with SessionLocal() as db:
            scheduled_matches = db.scalars(
                select(ScheduledMatch).where(last_check <= ScheduledMatch.time, ScheduledMatch.time <= datetime.now())
            ).all()
            if scheduled_matches:
                run_match(db, scheduled_matches[0])
            else:
                if environ.get("DEV"):
                    print(f"{datetime.now()}: no matches to run")
                last_check = datetime.now()
        now = datetime.now()
        for _ in range(60 - now.second):
            sleep(1)


if __name__ == "__main__":
    main()
