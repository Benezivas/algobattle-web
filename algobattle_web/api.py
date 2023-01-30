"Module specifying the json api actions."
from datetime import datetime
from typing import Any, Callable, Literal
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, Form, File, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse
from algobattle_web.battle import run_match
from algobattle_web.database import DbFile, autocommit, get_db, Session, ID
from algobattle_web.models import (
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
from algobattle_web.base_classes import BaseSchema, NoEdit


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
    name: str | None = None
    email: str | None = None


@router.post("/user/self/edit")
@autocommit
async def edit_self(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: EditSelf) -> User:
    for key, val in edit.dict(exclude_unset=True).items():
        setattr(user, key, val)
    return user


class EditSettings(BaseSchema):
    selected_team: ID | None = None


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
    name: str | None = None


@admin.post("/context/{id}/edit")
@autocommit
async def edit_context(*, db: Session = Depends(get_db), id: ID, data: EditContext) -> Context:
    context = unwrap(Context.get(db, id))
    if data.name is not None:
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
    name: str | None = None
    context: ID | None = None
    members: list[tuple[Literal["add", "remove"], ID]] | None = None


@admin.post("/team/{id}/edit")
@autocommit
def edit_team(*, db: Session = Depends(get_db), id: ID, edit: EditTeam) -> Team:
    team = unwrap(Team.get(db, id))
    if edit.name is not None:
        team.name = edit.name
    if edit.context is not None:
        team.context_id = edit.context
    if edit.members is not None:
        for action, user_id in edit.members:
            user = unwrap(db.get(User, user_id))
            match action:
                case "add":
                    if user in team.members:
                        raise HTTPException(400)
                    team.members.append(user)
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


@admin.post("/config/add")
@autocommit
async def add_config(*, db: Session = Depends(get_db), name: str = Form(), file: UploadFile = File()) -> Config:
    db_file = DbFile.create_from(file)
    return Config(db, name, db_file)


@router.get("/config/getfile/{id}")
@autocommit
async def get_config(*, db: Session = Depends(get_db), id: ID) -> FileResponse:
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return config.file.response()


class ConfigEdit(BaseSchema):
    id: ID
    name: str | None


@admin.post("/config/edit")
@autocommit
async def edit_config(
    *,
    db: Session = Depends(get_db),
    id: ID = Form(),
    name: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> Config:
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if file is None:
        config.update(db, name)
    else:
        config.update(db, name, file)
    return config


@admin.post("/config/delete/{id}")
@autocommit
async def delete_config(*, db: Session = Depends(get_db), id: ID) -> bool:
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    config.delete(db)
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
    config = Config.get(db, problem.config)
    if config is None:
        raise HTTPException(400)
    args: dict[str, Any] = problem.dict() | {"config": config}
    return Problem(db, **args)


@router.get("/problem/getfile/{id}")
@autocommit
async def get_problemfile(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    problem = Problem.get(db, id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not problem.visible_to(user):
        raise HTTPException(401)
    return problem.file.response()


@router.get("/problem/getdesc/{id}")
@autocommit
async def get_problem(*, db: Session = Depends(get_db), id: ID) -> FileResponse:
    problem = Problem.get(db, id)
    if problem is None or problem.description is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return problem.description.response()


class ProblemEdit(BaseSchema):
    id: ID
    name: str | None
    file: UploadFile | None = None
    config: ID | None = None
    start: datetime | None = None
    end: datetime | None = None
    desc: UploadFile | None = None


@admin.post("/problem/edit")
@autocommit
async def edit_problem(*, db: Session = Depends(get_db), edit: ProblemEdit = Depends(ProblemEdit.from_form())) -> Problem:
    problem = Problem.get(db, edit.id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    args = edit.dict()
    del args["id"]
    if edit.config is not None:
        args["config"] = Config.get(db, edit.config)
    problem.update(db, **args)
    return problem


@admin.post("/problem/delete/{id}")
@autocommit
async def delete_problem(*, db: Session = Depends(get_db), id: ID) -> bool:
    problem = Problem.get(db, id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    problem.delete(db)
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
async def add_program(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    program: ProgramCreate = Depends(ProgramCreate.from_form()),
) -> Program:
    if user.settings.selected_team is None:
        raise HTTPException(400)
    args = program.dict()
    args["problem"] = Problem.get(db, program.problem)
    if args["problem"] is None:
        raise HTTPException(400)
    return Program(db, team=user.settings.selected_team, **args)


@router.get("/program/getfile/{id}")
@autocommit
async def get_program_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    program = db.get(Program, id)
    if program is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not user.is_admin and program.team not in user.teams:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return program.file.response()


class ProgramEdit(BaseSchema):
    id: ID
    name: str | None = None
    role: Program.Role | None = None
    problem: ID | None = None


@router.post("/program/edit_own")
@autocommit
async def edit_own_program(
    *, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: ProgramEdit = Depends(ProgramEdit.from_form())
) -> Program:
    program = Program.get(db, edit.id)
    if program is None or user.settings.selected_team != program.team or program.locked:
        raise HTTPException(400)
    if edit.problem is not None:
        problem = Problem.get(db, edit.problem)
        if problem is None:
            raise HTTPException(400)
    else:
        problem = None
    program.update(db, name=edit.name, role=edit.role, problem=problem)
    return program


class ProgramEditAdmin(ProgramEdit):
    locked: bool | None = None


@admin.post("/program/edit")
@autocommit
async def edit_program(*, db: Session = Depends(get_db), edit: ProgramEditAdmin = Depends(ProgramEditAdmin.from_form())) -> Program:
    program = Program.get(db, edit.id)
    if program is None:
        raise HTTPException(400)
    if edit.problem is not None:
        problem = Problem.get(db, edit.problem)
        if problem is None:
            raise HTTPException(400)
    else:
        problem = None
    program.update(db, name=edit.name, role=edit.role, problem=problem, locked=edit.locked)
    return program


@admin.post("/program/delete/{id}")
@autocommit
async def delete_program(*, db: Session = Depends(get_db), id: ID) -> bool:
    program = Program.get(db, id)
    if program is None:
        raise HTTPException(400)
    program.delete(db)
    return True


# *******************************************************************************
# * Docs
# *******************************************************************************


class DocsUpload(BaseSchema):
    problem: ID
    file: UploadFile


@router.post("/documentation/upload")
@autocommit
async def upload_docs(
    db: Session = Depends(get_db), user: User = Depends(curr_user), data: DocsUpload = Depends(DocsUpload.from_form())
) -> Documentation:
    if user.settings.selected_team is None:
        raise HTTPException(400)
    problem = Problem.get(db, data.problem)
    if problem is None or not problem.visible_to(user):
        raise HTTPException(400)
    docs = Documentation.get(db, user.settings.selected_team, problem)
    if docs is None:
        file = DbFile.create_from(data.file)
        return Documentation(db, user.settings.selected_team, problem, file)
    else:
        docs.update(db, data.file)
        return docs


@router.get("/documentation/getfile/{id}")
@autocommit
async def get_docs_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID) -> FileResponse:
    docs = db.get(Documentation, id)
    if docs is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not user.is_admin and docs.team not in user.teams:
        raise HTTPException(401)
    return docs.file.response()


@router.post("/documentation/delete/{id}")
@autocommit
async def delete_docs(*, db: Session = Depends(get_db), id: ID) -> bool:
    docs = db.get(Documentation, id)
    if docs is None:
        raise HTTPException(400)
    docs.delete(db)
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
