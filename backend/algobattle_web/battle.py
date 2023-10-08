from datetime import datetime, timedelta
from time import sleep
from zipfile import ZipFile
from anyio import run
from sqlalchemy import select, create_engine

from algobattle.match import Match, AlgobattleConfig, TeamInfo, ProjectConfig
from algobattle.util import Role, TempDir, ExceptionInfo
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session, ID, Team
from algobattle_web.util import MatchStatus, install_packages, ServerConfig, SessionLocal


def run_match(db: Session, scheduled_match: ScheduledMatch):
    print(f"running match...")
    with TempDir() as folder:
        with ZipFile(scheduled_match.problem.file.path) as zipped:
            zipped.extractall(folder)
        config = AlgobattleConfig.from_file(folder / "algobattle.toml")
        config.teams = {}
        config.project = ProjectConfig(name_images=False, cleanup_images=True)
        install_packages(config.problem.dependencies)

        paricipants: dict[ID, ResultParticipant] = {}
        excluded_teams = set[Team]()
        for team in scheduled_match.problem.tournament.teams:
            gen = (
                db.scalars(select(Program).where(Program.team_id == team.id, Program.role == Role.generator))
                .unique()
                .first()
            )
            sol = (
                db.scalars(select(Program).where(Program.team_id == team.id, Program.role == Role.solver))
                .unique()
                .first()
            )

            if gen and sol:
                config.teams[team.name] = TeamInfo(generator=gen.file.path, solver=sol.file.path)
            else:
                excluded_teams.add(team)
            paricipants[team.id] = ResultParticipant(team, gen, sol, 0)
        db_result = MatchResult(MatchStatus.running, datetime.now(), scheduled_match.problem, set(paricipants.values()))
        db.add(db_result)
        db.commit()

        result = Match()
        run(result.run, config)
        result.excluded_teams |= {
            team.name: ExceptionInfo(type="RuntimeError", message="missing program") for team in excluded_teams
        }
        points = result.calculate_points(scheduled_match.points)

        for team in db_result.participants:
            team.points = points[team.team.name]
        db_result.status = MatchStatus.complete
        folder.joinpath("result.json").write_text(result.model_dump_json())
        db_result.logs = File.from_file(folder / "result.json", action="move")
        db.commit()


def run_scheduled_matches():
    time = datetime.now()
    first = time - ServerConfig.obj.match_execution_interval - timedelta(hours=1)
    with SessionLocal() as db:
        scheduled_matches = (
            db.scalars(select(ScheduledMatch).where(first <= ScheduledMatch.time, ScheduledMatch.time <= time))
            .unique()
            .all()
        )
        if len(scheduled_matches) == 0:
            return
        # ! Temporary fix, come up with a better solution to this
        if len(scheduled_matches) > 1:
            print("matches are scheduled too close together, aborting their execution!")
            return
        run_match(db, scheduled_matches[0])
        db.delete(scheduled_matches[0])
        db.commit()


def main():
    ServerConfig.load()
    engine = create_engine(ServerConfig.obj.database_url)
    SessionLocal.configure(bind=engine)
    day = datetime.today()
    while True:
        next_exec = (
            ServerConfig.obj.match_execution_interval
            - (datetime.now() - day) % ServerConfig.obj.match_execution_interval
        )
        sleep(next_exec.seconds)
        run_scheduled_matches()


if __name__ == "__main__":
    main()
