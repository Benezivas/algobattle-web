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
    autocommit,
    get_db,
    Session,
    ID,
    Config,
    Context,
    Documentation,
    MatchResult,
    ParticipantInfo,
    Problem,
    Program,
    Schedule,
    Team,
    User,
)
from algobattle_web.util import unwrap
from algobattle_web.dependencies import curr_user
from algobattle_web.base_classes import BaseSchema, Missing, missing, present


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)


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
def get_config(*, db: Session = Depends(get_db), id: ID) -> FileResponse:
    config = unwrap(Config.get(db, id))
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
    if not problem.visible_to(user):
        raise HTTPException(401)
    return problem.file.response()


@router.get("/problem/{id}/description")
@autocommit
async def get_problem(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    problem = unwrap(Problem.get(db, id))
    if not problem.visible_to(user):
        raise HTTPException(401)
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
    file = DbFile.create_from(data.file)
    return Program(db, data.name, team, data.role, file, problem)


@router.get("/program/{id}/file")
@autocommit
def get_program_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    program = unwrap(db.get(Program, id))
    if not user.is_admin and program.team not in user.teams:
        raise HTTPException(403)
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
    if not (program.user_editable and user.settings.selected_team == program.team):
        raise HTTPException(403)
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
def delete_program(*, db: Session = Depends(get_db), id: ID) -> bool:
    program = unwrap(Program.get(db, id))
    db.delete(program)
    return True


# *******************************************************************************
# * Docs
# *******************************************************************************


@router.post("/documentation/{problem_id}/upload")
@autocommit
async def upload_docs(*, db: Session = Depends(get_db), user: User = Depends(curr_user), problem_id: ID, file: UploadFile = File()) -> Documentation:
    team = unwrap(user.settings.selected_team)
    problem = unwrap(db.get(Problem, problem_id))
    if not problem.visible_to(user):
        raise HTTPException(400)
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
    if not user.is_admin and docs.team not in user.teams:
        raise HTTPException(401)
    return docs.file.response()


@router.post("/documentation/{id}/delete")
@autocommit
async def delete_docs(*, db: Session = Depends(get_db), id: ID) -> bool:
    docs = unwrap(db.get(Documentation, id))
    db.delete(docs)
    return True


# *******************************************************************************
# * Schedule
# *******************************************************************************


class ScheduleCreate(BaseSchema):
    name: str = ""
    time: datetime
    problem: ID
    config: ID | None
    participants: list[ParticipantInfo.Schema]
    points: int = 0


@admin.post("/schedule/create")
@autocommit
def create_schedule(*, db: Session = Depends(get_db), data: ScheduleCreate, background_tasks: BackgroundTasks) -> Schedule:
    problem = unwrap(Problem.get(db, data.problem))

    if data.config is None:
        config = None
    else:
        config = unwrap(Config.get(db, data.config))

    participants = [info.into_obj(db) for info in data.participants]

    schedule = Schedule.create(
        db, name=data.name, time=data.time, points=data.points, problem=problem, config=config, participants=participants
    )
    if schedule.time <= datetime.now():
        background_tasks.add_task(run_match, db, schedule)
    return schedule


class ScheduleEdit(BaseSchema):
    id: ID
    name: str | None = None
    time: datetime | None = None
    problem: ID | None = None
    config: ID | None | None = None
    points: int | None = None


@admin.post("/schedule/update")
@autocommit
def edit_schedule(*, db: Session = Depends(get_db), edit: ScheduleEdit) -> Schedule:
    schedule = unwrap(Schedule.get(db, edit.id))

    if edit.problem is None:
        problem = None
    else:
        problem = unwrap(Problem.get(db, edit.problem))

    if edit.config is None:
        config = None
    elif edit.config is None:
        config = None
    else:
        config = unwrap(Config.get(db, edit.config))

    schedule.update(db, name=edit.name, time=edit.time, problem=problem, config=config, points=edit.points)
    return schedule


@admin.post("/schedule/add_team")
@autocommit
def add_team(*, db: Session = Depends(get_db), id: ID, participant: ParticipantInfo.Schema) -> Schedule:
    schedule = unwrap(Schedule.get(db, id))
    schedule.update(db, add=[participant.into_obj(db)])
    return schedule


@admin.post("/schedule/remove_team")
@autocommit
def remove_team(*, db: Session = Depends(get_db), id: ID, team: ID) -> Schedule:
    schedule = unwrap(Schedule.get(db, id))
    team_obj = unwrap(Team.get(db, team))
    schedule.update(db, remove=[team_obj])
    return schedule


@admin.post("/schedule/delete/{id}")
@autocommit
def delete_schedule(*, db: Session = Depends(get_db), id: ID) -> bool:
    unwrap(Schedule.get(db, id)).delete(db)
    return True


# *******************************************************************************
# * Schedule
# *******************************************************************************

@router.get("/result/logs/{id}")
@autocommit
async def get_match_logs(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    result = unwrap(db.get(MatchResult, id))
    if user.is_admin or set(user.teams).intersection(p.team for p in result.participants):
        return unwrap(result.logs).response()
    else:
        raise HTTPException(401)


@admin.post("/result/delete/{id}")
@autocommit
def delete_result(*, db: Session = Depends(get_db), id: ID) -> bool:
    unwrap(MatchResult.get(db, id)).delete(db)
    return True


# * has to be executed after all route defns
router.include_router(admin)
