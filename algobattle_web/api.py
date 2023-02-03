"Module specifying the json api actions."
from datetime import datetime
from typing import Any, Callable, Literal, cast
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, Form, File, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse
from algobattle_web.battle import run_match
from algobattle_web.models import (
    DbFile,
    MatchParticipant,
    autocommit,
    get_db,
    Session,
    ID,
    Config,
    Context,
    Documentation,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
)
from algobattle_web.util import unwrap, BaseSchema, Missing, missing, present
from algobattle_web.dependencies import curr_user, check_if_admin


class SchemaRoute(APIRoute):
    """Route that defaults to using the `Schema` entry of the returned object as a response_model."""

    def __init__(self, path: str, endpoint: Callable[..., Any], *, response_model: Any = Default(None), **kwargs) -> None:
        if isinstance(response_model, DefaultPlaceholder):
            return_annotation = get_typed_return_annotation(endpoint)
            if hasattr(return_annotation, "Schema"):
                response_model = return_annotation.Schema
        super().__init__(path, endpoint, response_model=response_model, **kwargs)


router = APIRouter(prefix="/api", tags=["api"], route_class=SchemaRoute)
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)], route_class=SchemaRoute)

# *******************************************************************************
# * User
# *******************************************************************************


class CreateUser(BaseSchema):
    name: str
    email: str
    is_admin: bool = False


@admin.post("/user/create")
@autocommit
async def create_user(*, db: Session = Depends(get_db), user: CreateUser) -> User:
    return User(db=db, email=user.email, name=user.name, is_admin=user.is_admin)


class EditUser(BaseSchema):
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None


@admin.post("/user/{id}/edit")
@autocommit
async def edit_user(*, db: Session = Depends(get_db), id: ID, edit: EditUser) -> User:
    user = unwrap(User.get(db, id))
    for key, val in edit.dict(exclude_unset=True).items():
        setattr(user, key, val)
    return user


@admin.post("/user/{id}/delete")
@autocommit
async def delete_user(*, db: Session = Depends(get_db), id: ID) -> bool:
    user = unwrap(User.get(db, id))
    db.delete(user)
    return True


class EditSelf(BaseSchema):
    name: str | Missing = missing
    email: str | Missing = missing


@router.post("/user/self/edit")
@autocommit
async def edit_self(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: EditSelf) -> User:
    for key, val in edit.dict(exclude_unset=True).items():
        setattr(user, key, val)
    return user


class EditSettings(BaseSchema):
    selected_team: ID | Missing = missing


@router.post("/user/self/settings")
@autocommit
async def edit_settings(*, db: Session = Depends(get_db), user: User = Depends(curr_user), settings: EditSettings) -> User:
    updates = settings.dict(exclude_unset=True)
    if "selected_team" in "updates":
        team = unwrap(Team.get(db, updates["selected_team"]))
        if team not in user.teams:
            raise HTTPException(status.HTTP_400_BAD_REQUEST)
        user.settings.selected_team = team
    return user


# *******************************************************************************
# * Context
# *******************************************************************************


class CreateContext(BaseSchema):
    name: str


@admin.post("/context/create")
@autocommit
async def create_context(*, db: Session = Depends(get_db), context: CreateContext) -> Context:
    return Context(db, context.name)


class EditContext(BaseSchema):
    name: str | Missing = missing


@admin.post("/context/{id}/edit")
@autocommit
async def edit_context(*, db: Session = Depends(get_db), id: ID, data: EditContext) -> Context:
    context = unwrap(Context.get(db, id))
    if present(data.name):
        context.name = data.name
    return context


@admin.post("/context/{id}/delete")
@autocommit
async def delete_context(*, db: Session = Depends(get_db), id: ID) -> bool:
    context = unwrap(Context.get(db, id))
    db.delete(context)
    return True


# *******************************************************************************
# * Team
# *******************************************************************************


class CreateTeam(BaseSchema):
    name: str
    context: ID


@admin.post("/team/create")
@autocommit
def create_team(*, db: Session = Depends(get_db), team: CreateTeam) -> Team:
    context = unwrap(Context.get(db, team.context))
    return Team(db, team.name, context)


class EditTeam(BaseSchema):
    name: str | Missing = missing
    context: ID | Missing = missing
    members: list[tuple[Literal["add", "remove"], ID]] | Missing = missing


@admin.post("/team/{id}/edit")
@autocommit
def edit_team(*, db: Session = Depends(get_db), id: ID, edit: EditTeam) -> Team:
    team = unwrap(Team.get(db, id))
    if present(edit.name):
        team.name = edit.name
    if present(edit.context):
        team.context_id = edit.context
    if present(edit.members):
        for action, user_id in edit.members:
            user = unwrap(db.get(User, user_id))
            match action:
                case "add":
                    if user in team.members:
                        raise HTTPException(400)
                    team.members.append(user)
                    if len(user.teams) == 1:
                        user.settings.selected_team = team
                case "remove":
                    if user not in team.members:
                        raise HTTPException(400)
                    team.members.remove(user)
    return team


@admin.post("/team/{id}/delete")
@autocommit
def delete_team(*, db: Session = Depends(get_db), id: ID) -> bool:
    team = unwrap(Team.get(db, id))
    db.delete(team)
    return True


class MemberEditTeam(BaseSchema):
    name: str | None = None


@router.post("/team/self/edit")
@autocommit
def member_edit_team(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: MemberEditTeam) -> Team:
    team = unwrap(user.settings.selected_team)
    team.assert_editable(user)
    if edit.name is not None:
        team.name = edit.name
    return team


# *******************************************************************************
# * Config
# *******************************************************************************


@admin.post("/config/create")
@autocommit
def add_config(*, db: Session = Depends(get_db), name: str = Form(), file: UploadFile = File()) -> Config:
    db_file = DbFile.create_from(file)
    return Config(db, name, db_file)


@router.get("/config/{id}/file")
@autocommit
def get_config(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    config = unwrap(Config.get(db, id))
    config.assert_visible(user)
    return config.file.response()


class ConfigEdit(BaseSchema):
    id: ID
    name: str | Missing = missing


@admin.post("/config/{id}/edit")
@autocommit
def edit_config(
    *,
    db: Session = Depends(get_db),
    id: ID,
    name: str | Missing = Form(default=missing),
    file: UploadFile | Missing = File(default=missing),
) -> Config:
    config = unwrap(Config.get(db, id))
    if present(name):
        config.name = name
    if present(file):
        config.file.attach(file)
    return config


@admin.post("/config/{id}/delete")
@autocommit
def delete_config(*, db: Session = Depends(get_db), id: ID) -> bool:
    config = unwrap(Config.get(db, id))
    db.delete(config)
    return True


# *******************************************************************************
# * Problem
# *******************************************************************************


class ProblemCreate(BaseSchema):
    name: str
    file: UploadFile
    config: ID
    start: datetime | None = None
    end: datetime | None = None
    description: UploadFile | None = None


@admin.post("/problem/create")
@autocommit
async def add_problem(*, db: Session = Depends(get_db), problem: ProblemCreate = Depends(ProblemCreate.from_form())) -> Problem:
    config = unwrap(Config.get(db, problem.config))
    file = DbFile.create_from(problem.file)
    if problem.description is not None:
        desc = DbFile.create_from(problem.description)
    else:
        desc = None
    return Problem(db, problem.name, file, config, problem.start, problem.end, desc)


@router.get("/problem/{id}/file")
@autocommit
async def get_problemfile(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    problem = unwrap(Problem.get(db, id))
    problem.assert_visible(user)
    return problem.file.response()


@router.get("/problem/{id}/description")
@autocommit
async def get_problem(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    problem = unwrap(Problem.get(db, id))
    problem.assert_visible(user)
    return unwrap(problem.description).response()


class ProblemEdit(BaseSchema):
    name: str | Missing = missing
    file: UploadFile | Missing = missing
    config: ID | Missing = missing
    start: datetime | None | Missing = missing
    end: datetime | None | Missing = missing
    description: UploadFile | None | Missing = missing


@admin.post("/problem/{id}/edit")
@autocommit
async def edit_problem(*, db: Session = Depends(get_db), id: ID, edit: ProblemEdit = Depends(ProblemEdit.from_form())) -> Problem:
    problem = unwrap(db.get(Problem, id))
    for key in ("name", "start", "end"):
        val = getattr(edit, key)
        if present(val):
            setattr(problem, key, val)
    if present(edit.file):
        problem.file.attach(edit.file)
    if present(edit.description):
        if edit.description is None:
            problem.description = None
        elif problem.description is None:
            problem.description = DbFile.create_from(edit.description)
        else:
            problem.description.attach(edit.description)
    if present(edit.config):
        problem.config_id = edit.config
    return problem


@admin.post("/problem/{id}/delete")
@autocommit
async def delete_problem(*, db: Session = Depends(get_db), id: ID) -> bool:
    problem = unwrap(db.get(Problem, id))
    db.delete(problem)
    return True


# *******************************************************************************
# * Program
# *******************************************************************************


class ProgramCreate(BaseSchema):
    name: str
    role: Program.Role
    file: UploadFile
    problem: ID


@router.post("/program/create")
@autocommit
def add_program(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    data: ProgramCreate = Depends(ProgramCreate.from_form()),
) -> Program:
    team = unwrap(user.settings.selected_team)
    problem = unwrap(db.get(Problem, data.problem))
    problem.assert_visible(user)
    file = DbFile.create_from(data.file)
    return Program(db, data.name, team, data.role, file, problem)


@router.get("/program/{id}/file")
@autocommit
def get_program_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    program = unwrap(db.get(Program, id))
    program.assert_visible(user)
    return program.file.response()


class ProgramEdit(BaseSchema):
    name: str | Missing = missing
    role: Program.Role | Missing = missing
    problem: ID | Missing = missing


@router.post("/program/{id}/edit")
@autocommit
def edit_own_program(
    *, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID, edit: ProgramEdit = Depends(ProgramEdit.from_form())
) -> Program:
    program = unwrap(db.get(Program, id))
    program.assert_editable(user)
    if present(edit.name):
        program.name = edit.name
    if present(edit.role):
        program.role = cast(Program.Role, edit.role)
    if present(edit.problem):
        program.problem_id = edit.problem
    return program


@admin.post("/program/{id}/user_editable")
@autocommit
def edit_program(*, db: Session = Depends(get_db), id: ID, user_editable: bool) -> Program:
    program = unwrap(db.get(Program, id))
    program.user_editable = user_editable
    return program


@router.post("/program/{id}/delete")
@autocommit
def delete_program(*, db: Session = Depends(get_db), user = Depends(curr_user), id: ID) -> bool:
    program = unwrap(Program.get(db, id))
    program.assert_editable(user)
    db.delete(program)
    return True


# *******************************************************************************
# * Docs
# *******************************************************************************


@router.post("/documentation/upload")
@autocommit
async def upload_docs(*, db: Session = Depends(get_db), user: User = Depends(curr_user), problem_id: ID = Form(), file: UploadFile = File()) -> Documentation:
    team = unwrap(user.settings.selected_team)
    problem = unwrap(db.get(Problem, problem_id))
    problem.assert_editable(user)
    docs = Documentation.get(db, team, problem)
    if docs is None:
        _file = DbFile.create_from(file)
        return Documentation(db, team, problem, _file)
    else:
        docs.file.attach(file)
        return docs


@router.get("/documentation/{id}/file")
@autocommit
async def get_docs_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    docs = unwrap(db.get(Documentation, id))
    docs.assert_visible(user)
    return docs.file.response()


@router.post("/documentation/{id}/delete")
@autocommit
async def delete_docs(*, db: Session = Depends(get_db), user = Depends(curr_user), id: ID) -> bool:
    docs = unwrap(db.get(Documentation, id))
    docs.assert_editable(user)
    db.delete(docs)
    return True


# *******************************************************************************
# * Match
# *******************************************************************************


class ScheduledMatchCreate(BaseSchema):
    name: str = ""
    time: datetime
    problem: ID
    config: ID | None
    participants: dict[ID, MatchParticipant.Schema]
    points: float = 0


@admin.post("/match/schedule/create")
@autocommit
def create_schedule(*, db: Session = Depends(get_db), data: ScheduledMatchCreate, background_tasks: BackgroundTasks) -> ScheduledMatch:
    problem = unwrap(Problem.get(db, data.problem))
    config = unwrap(Config.get(db, data.config)) if data.config is not None else None
    schedule = ScheduledMatch(db, data.time, problem, config, data.name, data.points)
    for team_id, info in data.participants.items():
        team = unwrap(db.get(Team, team_id))
        gen = unwrap(db.get(Program, info.generator)) if info.generator is not None else None
        sol = unwrap(db.get(Program, info.solver)) if info.solver is not None else None
        schedule.participants.add(MatchParticipant(db, schedule, team, gen, sol))

    #! Prototype
    if schedule.time <= datetime.now():
        background_tasks.add_task(run_match, db, schedule)
    return schedule


class ScheduleEdit(BaseSchema):
    class Participant(BaseSchema):
        generator: ID | None | Missing = missing
        solver: ID | None | Missing = missing

    name: str | Missing = missing
    time: datetime | Missing = missing
    problem: ID | Missing = missing
    config: ID | None | Missing = missing
    points: float | Missing = missing
    participants: dict[ID, Participant | None] | Missing = missing


@admin.post("/match/schedule/{id}/edit")
@autocommit
def edit_schedule(*, db: Session = Depends(get_db), edit: ScheduleEdit) -> ScheduledMatch:
    match = unwrap(db.get(ScheduledMatch, id))
    if present(edit.name):
        match.name = edit.name
    if present(edit.problem):
        match.problem = unwrap(db.get(Problem, edit.problem))
    if present(edit.config):
        match.config = unwrap(db.get(Config, edit.config))
    if present(edit.points):
        match.points = edit.points
    if present(edit.participants):
        participants = {p.team: p for p in match.participants}
        for team_id, info in edit.participants.items():
            team = unwrap(db.get(Team, team_id))
            if info is None:
                if team not in participants:
                    raise ValueError
                match.participants.discard(participants[team])
            elif team not in participants:
                if not present(info.generator) or not present(info.solver):
                    raise ValueError
                gen = db.get(Program, info.generator) if info.generator is not None else None
                sol = db.get(Program, info.solver) if info.solver is not None else None
                match.participants.add(MatchParticipant(db, match, team, gen, sol))
            else:
                if present(info.generator):
                    participants[team].generator = unwrap(db.get(Program, info.generator))
                if present(info.solver):
                    participants[team].solver = unwrap(db.get(Program, info.solver))
    return match


@admin.post("/match/schedule/{id}/delete")
@autocommit
def delete_schedule(*, db: Session = Depends(get_db), id: ID) -> bool:
    match = unwrap(ScheduledMatch.get(db, id))
    db.delete(match)
    return True


@router.get("/match/result/{id}/logs")
@autocommit
async def get_match_logs(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    result = unwrap(db.get(MatchResult, id))
    result.assert_visible(user)
    return unwrap(result.logs).response()


@admin.post("/match/result/{id}/delete")
@autocommit
def delete_result(*, db: Session = Depends(get_db), id: ID) -> bool:
    result = unwrap(MatchResult.get(db, id))
    db.delete(result)
    return True


# * has to be executed after all route defns
router.include_router(admin)
