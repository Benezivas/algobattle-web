"Module specifying the json api actions."
from __future__ import annotations
from datetime import datetime
from typing import Tuple
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, Form, File
from algobattle_web.database import get_db, Session, ID
from algobattle_web.models import (
    Config,
    Context,
    Documentation,
    ParticipantInfo,
    Problem,
    Program,
    Schedule,
    ScheduleParticipant,
    Team,
    User,
    UserSettings,
)
from algobattle_web.util import unwrap
from algobattle_web.dependencies import curr_user
from algobattle_web.base_classes import BaseSchema, NoEdit


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)


router = APIRouter(prefix="/api", tags=["api"])
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)])

# *******************************************************************************
# * User
# *******************************************************************************


class CreateUser(BaseSchema):
    name: str
    email: str
    is_admin: bool = False


@admin.post("/user/create", response_model=User.Schema)
async def create_user(*, db: Session = Depends(get_db), user: CreateUser):
    return User.create(db, user.email, user.name, user.is_admin)


class EditUser(BaseSchema):
    id: ID
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None


@admin.post("/user/edit", response_model=User.Schema)
async def edit_user(*, db: Session = Depends(get_db), edit: EditUser):
    user = User.get(db, edit.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    user.update(db, edit.email, edit.name, edit.is_admin)
    return user


class DeleteUser(BaseSchema):
    id: ID


@admin.post("/user/delete")
async def delete_user(*, db: Session = Depends(get_db), user_schema: DeleteUser):
    user = User.get(db, user_schema.id)
    if user is None:
        return False
    else:
        user.delete(db)
        return True


class EditSelf(BaseSchema):
    name: str | None = None
    email: str | None = None


@router.post("/user/edit_self", response_model=User.Schema)
async def edit_self(*, db: Session = Depends(get_db), user=Depends(curr_user), edit: EditSelf):
    user = User.get(db, user.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    user.update(db, edit.email, edit.name)
    return user


class EditSettings(BaseSchema):
    selected_team: ID | None


@router.post("/user/edit_settings", response_model=UserSettings.Schema)
async def edit_settings(*, db: Session = Depends(get_db), user: User = Depends(curr_user), settings: EditSettings):
    print(settings)
    if settings.selected_team is not None:
        team = Team.get(db, settings.selected_team)
        if team is None or team not in user.teams:
            raise HTTPException(status.HTTP_400_BAD_REQUEST)
        user.settings.selected_team = team
    db.commit()
    return user


# *******************************************************************************
# * Context
# *******************************************************************************


class CreateContext(BaseSchema):
    name: str


@admin.post("/context/create", response_model=Context.Schema)
async def create_context(*, db: Session = Depends(get_db), context: CreateContext):
    return Context.create(db, context.name)


class EditContext(BaseSchema):
    id: ID
    name: str | None


@admin.post("/context/edit", response_model=Context.Schema)
async def edit_context(*, db: Session = Depends(get_db), edit: EditContext):
    context = Context.get(db, edit.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.update(db, name=edit.name)
    return context


class DeleteContext(BaseSchema):
    id: ID


@admin.post("/context/delete")
async def delete_context(*, db: Session = Depends(get_db), context_schema: DeleteContext):
    context = Context.get(db, context_schema.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.delete(db)
    return True


# *******************************************************************************
# * Team
# *******************************************************************************


class CreateTeam(BaseSchema):
    name: str
    context: ID


@admin.post("/team/create", response_model=Team.Schema)
async def create_team(*, db: Session = Depends(get_db), team: CreateTeam):
    context = Context.get(db, team.context)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return Team.create(db, team.name, context)


class EditTeam(BaseSchema):
    id: ID
    name: str | None = None
    context: ID | str | Context.Schema


@admin.post("/team/edit", response_model=Team.Schema)
async def edit_team(*, db: Session = Depends(get_db), edit: EditTeam):
    team = Team.get(db, edit.id)
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if isinstance(edit.context, Context.Schema):
        edit.context = edit.context.id
    team.update(db, edit.name, edit.context)
    return team


class DeleteTeam(BaseSchema):
    id: ID


@admin.post("/team/delete")
async def delete_team(*, db: Session = Depends(get_db), team_schema: DeleteTeam):
    team = Team.get(db, team_schema.id)
    if team is None:
        return False
    else:
        team.delete(db)
        return True


class MemberEditTeam(BaseSchema):
    id: ID
    name: str


@router.post("/team/member_edit", response_model=Team.Schema)
async def member_edit_team(*, db: Session = Depends(get_db), curr: User = Depends(curr_user), edit: MemberEditTeam):
    team = Team.get(db, edit.id)
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not any(team.id == t.id for t in curr.teams):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    team.update(db, name=edit.name)
    return team


class EditTeamMember(BaseSchema):
    team: ID
    user: ID


@admin.post("/team/add_member", response_model=Tuple[Team.Schema, User.Schema])
async def add_team_member(*, db: Session = Depends(get_db), info: EditTeamMember):
    user = User.get(db, info.user)
    team = Team.get(db, info.team)
    if user is None or team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    team.add_member(db, user)
    return team, user


@admin.post("/team/remove_member", response_model=Tuple[Team.Schema, User.Schema])
async def remove_team_member(*, db: Session = Depends(get_db), info: EditTeamMember):
    user = User.get(db, info.user)
    team = Team.get(db, info.team)
    if user is None or team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    team.remove_member(db, user)
    return team, user


# *******************************************************************************
# * Config
# *******************************************************************************


@admin.post("/config/add", response_model=Config.Schema)
async def add_config(*, db: Session = Depends(get_db), name: str = Form(), file: UploadFile = File()):
    return Config.create(db, name, file)


@router.get("/config/getfile/{id}")
async def get_config(*, db: Session = Depends(get_db), id: ID):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return config.file.response()


class ConfigEdit(BaseSchema):
    id: ID
    name: str | None


@admin.post("/config/edit", response_model=Config.Schema)
async def edit_config(
    *,
    db: Session = Depends(get_db),
    id: ID = Form(),
    name: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if file is None:
        config.update(db, name)
    else:
        config.update(db, name, file)
    return config


@admin.post("/config/delete/{id}")
async def delete_config(*, db: Session = Depends(get_db), id: ID):
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


@admin.post("/problem/create", response_model=Problem.Schema)
async def add_problem(*, db: Session = Depends(get_db), problem: ProblemCreate = Depends(ProblemCreate.from_form())):
    config = Config.get(db, problem.config)
    if config is None:
        raise HTTPException(400)
    args = problem.dict() | {"config": config}
    return Problem.create(db, **args)


@router.get("/problem/getfile/{id}")
async def get_problemfile(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID):
    problem = Problem.get(db, id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not problem.visible_to(user):
        raise HTTPException(401)
    return problem.file.response()


@router.get("/problem/getdesc/{id}")
async def get_problem(*, db: Session = Depends(get_db), id: ID):
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


@admin.post("/problem/edit", response_model=Problem.Schema)
async def edit_problem(*, db: Session = Depends(get_db), edit: ProblemEdit = Depends(ProblemEdit.from_form())):
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
async def delete_problem(*, db: Session = Depends(get_db), id: ID):
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


@router.post("/program/create", response_model=Program.Schema)
async def add_program(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    program: ProgramCreate = Depends(ProgramCreate.from_form()),
):
    if user.settings.selected_team is None:
        raise HTTPException(400)
    args = program.dict()
    args["problem"] = Problem.get(db, program.problem)
    if args["problem"] is None:
        raise HTTPException(400)
    return Program.create(db, team=user.settings.selected_team, **args)


@router.get("/program/getfile/{id}")
async def get_program_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID):
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


@router.post("/program/edit_own", response_model=Program.Schema)
async def edit_own_program(
    *, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: ProgramEdit = Depends(ProgramEdit.from_form())
):
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


@admin.post("/program/edit", response_model=Program.Schema)
async def edit_program(*, db: Session = Depends(get_db), edit: ProgramEditAdmin = Depends(ProgramEditAdmin.from_form())):
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
async def delete_program(*, db: Session = Depends(get_db), id: ID):
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


@router.post("/documentation/upload", response_model=Documentation.Schema)
async def upload_docs(
    db: Session = Depends(get_db), user: User = Depends(curr_user), data: DocsUpload = Depends(DocsUpload.from_form())
):
    if user.settings.selected_team is None:
        raise HTTPException(400)
    problem = Problem.get(db, data.problem)
    if problem is None or not problem.visible_to(user):
        raise HTTPException(400)
    docs = Documentation.get(db, user.settings.selected_team, problem)
    if docs is None:
        return Documentation.create(db, user.settings.selected_team, problem, data.file)
    else:
        docs.update(db, data.file)
        return docs


@router.get("/documentation/getfile/{id}")
async def get_docs_file(*, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID):
    docs = db.get(Documentation, id)
    if docs is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not user.is_admin and docs.team not in user.teams:
        raise HTTPException(401)
    return docs.file.response()


@router.post("/documentation/delete/{id}")
async def delete_docs(*, db: Session = Depends(get_db), id: ID):
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


@admin.post("/schedule/create", response_model=Schedule.Schema)
def create_schedule(*, db: Session = Depends(get_db), data: ScheduleCreate):
    problem = unwrap(Problem.get(db, data.problem))

    if data.config is None:
        config = None
    else:
        config = unwrap(Config.get(db, data.config))

    participants = [info.into_obj(db) for info in data.participants]

    return Schedule.create(
        db, name=data.name, time=data.time, points=data.points, problem=problem, config=config, participants=participants
    )


class ScheduleEdit(BaseSchema):
    id: ID
    name: str | NoEdit = NoEdit()
    time: datetime | NoEdit = NoEdit()
    problem: ID | NoEdit = NoEdit()
    config: ID | None | NoEdit = NoEdit()
    points: int | NoEdit = NoEdit()


@admin.post("/schedule/update", response_model=Schedule.Schema)
def edit_schedule(*, db: Session = Depends(get_db), edit: ScheduleEdit):
    schedule = unwrap(Schedule.get(db, edit.id))

    if isinstance(edit.problem, NoEdit):
        problem = NoEdit()
    else:
        problem = unwrap(Problem.get(db, edit.problem))

    if isinstance(edit.config, NoEdit):
        config = NoEdit()
    elif edit.config is None:
        config = None
    else:
        config = unwrap(Config.get(db, edit.config))

    schedule.update(db, name=edit.name, time=edit.time, problem=problem, config=config, points=edit.points)
    return schedule


@admin.post("/schedule/add_team", response_model=Schedule.Schema)
def add_team(*, db: Session = Depends(get_db), id: ID, participant: ParticipantInfo.Schema):
    schedule = unwrap(Schedule.get(db, id))
    schedule.update(db, add=[participant.into_obj(db)])
    return schedule


@admin.post("/schedule/remove_team", response_model=Schedule.Schema)
def remove_team(*, db: Session = Depends(get_db), id: ID, team: ID):
    schedule = unwrap(Schedule.get(db, id))
    team_obj = unwrap(Team.get(db, team))
    schedule.update(db, remove=[team_obj])
    return schedule


@admin.post("/schedule/delete/{id}")
def delete_schedule(*, db: Session = Depends(get_db), id: ID):
    unwrap(Schedule.get(db, id)).delete(db)
    return True


# * has to be executed after all route defns
router.include_router(admin)
