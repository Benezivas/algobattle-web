from datetime import datetime, timedelta
from time import sleep
from zipfile import ZipFile
from anyio import run
from sqlalchemy import select, create_engine

from algobattle.match import Match, AlgobattleConfig, TeamInfo, ProjectConfig
from algobattle.util import Role, TempDir
from algobattle_web.models import MatchResult, Program, ResultParticipant, ScheduledMatch, File, Session, ID
from algobattle_web.util import MatchStatus, install_packages, unwrap, ServerConfig, SessionLocal


def run_match(db: Session, scheduled_match: ScheduledMatch):
    print(f"running match...")
    with TempDir() as folder:
        with ZipFile(scheduled_match.problem.file.path) as zipped:
            zipped.extractall(folder)
        config = AlgobattleConfig.from_file(folder / "algobattle.toml")
        config.teams = {}
        config.project = ProjectConfig(name_images=False, cleanup_images=True)
        config.problem.location = scheduled_match.problem.file.path
        install_packages(config.problem.dependencies)

        paricipants: dict[ID, ResultParticipant] = {}
        for team in scheduled_match.problem.tournament.teams:
            gen = unwrap(
                db.scalars(select(Program).where(Program.team_id == team.id, Program.role == Role.generator))
                .unique()
                .first()
            )
            sol = unwrap(
                db.scalars(select(Program).where(Program.team_id == team.id, Program.role == Role.solver))
                .unique()
                .first()
            )

            config.teams[team.name] = TeamInfo(generator=gen.file.path, solver=sol.file.path)
            paricipants[team.id] = ResultParticipant(team, gen, sol, 0)
        db_result = MatchResult(MatchStatus.running, datetime.now(), scheduled_match.problem, set(paricipants.values()))
        db.add(db_result)
        db.commit()

        result = run(Match.run, config)
        points = result.calculate_points(scheduled_match.points)

        for team in db_result.participants:
            team.points = points[team.team.name]
        db_result.status = MatchStatus.complete
        with open(folder / "result.json", "x") as f:
            f.write(result.model_dump_json())
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
        try:
            run_match(db, scheduled_matches[0])
        except BaseException as e:
            print(f"Exception occured when executing match:\n{e}")
        finally:
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
