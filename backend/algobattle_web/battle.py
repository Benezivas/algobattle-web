from datetime import datetime
from time import sleep
from zipfile import ZipFile
from anyio import run
from sqlalchemy import select, create_engine

from algobattle.match import Match, AlgobattleConfig, TeamInfo, ProjectConfig
from algobattle.util import Role, TempDir, ExceptionInfo
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session, ID
from algobattle_web.util import EnvConfig, MatchStatus, install_packages, SessionLocal


def run_match(db: Session, scheduled_match: ScheduledMatch):
    print(f"running match {scheduled_match.name} scheduled at {scheduled_match.time}")
    with TempDir() as folder:
        with ZipFile(scheduled_match.problem.file.path) as zipped:
            zipped.extractall(folder)
        config = AlgobattleConfig.from_file(folder / "algobattle.toml")
        config.teams = {}
        config.project = ProjectConfig(name_images=False, cleanup_images=True)
        install_packages(config.problem.dependencies)

        paricipants: dict[ID, ResultParticipant] = {}
        excluded_teams = set[str]()
        for team in scheduled_match.problem.tournament.teams:
            gen = (
                db.scalars(
                    select(Program).where(
                        Program.team_id == team.id,
                        Program.problem_id == scheduled_match.problem_id,
                        Program.role == Role.generator,
                    ).order_by(Program.creation_time.desc()).limit(1)
                )
                .unique()
                .first()
            )
            sol = (
                db.scalars(
                    select(Program).where(
                        Program.team_id == team.id,
                        Program.problem_id == scheduled_match.problem_id,
                        Program.role == Role.solver,
                    ).order_by(Program.creation_time.desc()).limit(1)
                )
                .unique()
                .first()
            )

            if gen and sol:
                config.teams[team.name] = TeamInfo(generator=gen.file.path, solver=sol.file.path)
            else:
                excluded_teams.add(team.name)
            paricipants[team.id] = ResultParticipant(team, gen, sol, 0)
        db_result = MatchResult(MatchStatus.running, datetime.now(), scheduled_match.problem, set(paricipants.values()))
        db.add(db_result)
        db.commit()

        result = Match()
        run(result.run, config)
        result.excluded_teams |= {
            team: ExceptionInfo(type="RuntimeError", message="missing program") for team in excluded_teams
        }
        points = result.calculate_points(scheduled_match.points)

        for team in db_result.participants:
            team.points = points[team.team.name]
        db_result.status = MatchStatus.complete
        folder.joinpath("result.json").write_text(result.model_dump_json())
        db_result.logs = File.from_file(folder / "result.json", action="move")
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
                print(f"{datetime.now()}: no matches to run")
                last_check = datetime.now()
        now = datetime.now()
        sleep(60 - (now.second - now.microsecond / 1_000_000))


if __name__ == "__main__":
    main()
