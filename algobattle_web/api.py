"Module specifying the json api actions."
from __future__ import annotations
from datetime import datetime
from typing import Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, Form, File

from algobattle_web.database import get_db, Session
from algobattle_web.models import Config, Context, Problem, Team, User
from algobattle_web.util import curr_user
from algobattle_web.base_classes import BaseSchema


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

router = APIRouter(prefix="/api", tags=["api"])
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)])

#*******************************************************************************
#* User
#*******************************************************************************

class CreateUser(BaseSchema):
    name: str
    email: str
    is_admin: bool = False


@admin.post("/user/create", response_model=User.Schema)
async def create_user(*, db: Session = Depends(get_db), user: CreateUser):
    return User.create(db, user.email, user.name, user.is_admin)


class EditUser(BaseSchema):
    id: UUID
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
    id: UUID

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

@router.post("/user/edit_self")
async def edit_self(*, db: Session = Depends(get_db), user = Depends(curr_user), edit: EditSelf):
    user = User.get(db, user.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    user.update(db, edit.email, edit.name)
    
#*******************************************************************************
#* Context
#*******************************************************************************

class CreateContext(BaseSchema):
    name: str

@admin.post("/context/create", response_model=Context.Schema)
async def create_context(*, db: Session = Depends(get_db), context: CreateContext):
    return Context.create(db, context.name)

class EditContext(BaseSchema):
    id: UUID
    name: str | None

@admin.post("/context/edit", response_model=Context.Schema)
async def edit_context(*, db: Session = Depends(get_db), edit: EditContext):
    context = Context.get(db, edit.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.update(db, name=edit.name)
    return context

class DeleteContext(BaseSchema):
    id: UUID

@admin.post("/context/delete")
async def delete_context(*, db: Session = Depends(get_db), context_schema: DeleteContext):
    context = Context.get(db, context_schema.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.delete(db)
    return True

#*******************************************************************************
#* Team
#*******************************************************************************

class CreateTeam(BaseSchema):
    name: str
    context: UUID

@admin.post("/team/create", response_model=Team.Schema)
async def create_team(*, db: Session = Depends(get_db), team: CreateTeam):
    context = Context.get(db, team.context)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return Team.create(db, team.name, context)

class EditTeam(BaseSchema):
    id: UUID
    name: str | None = None
    context: UUID | str | Context.Schema

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
    id: UUID

@admin.post("/team/delete")
async def delete_team(*, db: Session = Depends(get_db), team_schema: DeleteTeam):
    team = Team.get(db, team_schema.id)
    if team is None:
        return False
    else:
        team.delete(db)
        return True

class MemberEditTeam(BaseSchema):
    id: UUID
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
    team: UUID
    user: UUID

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

#*******************************************************************************
#* Config
#*******************************************************************************

@admin.post("/config/add", response_model=Config.Schema)
async def add_config(*, db: Session = Depends(get_db), name: str = Form(), file: UploadFile = File()):
    return Config.create(db, name, file)


@router.get("/config/getfile/{id}")
async def get_config(*, db: Session = Depends(get_db), id: UUID):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return config.file.response()

class ConfigEdit(BaseSchema):
    id: UUID
    name: str | None

@admin.post("/config/edit", response_model=Config.Schema)
async def edit_config(*, db: Session = Depends(get_db), id: UUID = Form(), name: str | None = Form(default=None), file: UploadFile | None = File(default=None)):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if file is None:
        config.update(db, name)
    else:
        config.update(db, name, file)
    return config

@admin.post("/config/delete/{id}")
async def delete_config(*, db: Session = Depends(get_db), id: UUID):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    config.delete(db)
    return True

#*******************************************************************************
#* Problem
#*******************************************************************************

@admin.post("/problem/add", response_model=Config.Schema)
async def add_problem(*, db: Session = Depends(get_db), name: str = Form(), file: UploadFile = File(),
    config: UUID = Form(), start: datetime | None = Form(default=None), end: datetime | None = Form(default=None),
    description: UploadFile | None = File(default=None)):
    config_obj = Config.get(db, config)
    if config_obj is None:
        raise HTTPException(400)
    return Problem.create(db, name, file, config_obj, start, end, description)

@router.get("/problem/getfile/{id}")
async def get_problemfile(*, db: Session = Depends(get_db), id: UUID):
    problem = Problem.get(db, id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return problem.file.response()

@router.get("/problem/getdesc/{id}")
async def get_problem(*, db: Session = Depends(get_db), id: UUID):
    problem = Problem.get(db, id)
    if problem is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    return problem.file.response()

@admin.post("/problem/edit", response_model=Config.Schema)
async def edit_problem(*, db: Session = Depends(get_db), id: UUID = Form(), name: str | None = Form(default=None), file: UploadFile | None = File(default=None),
    config: UUID | None = Form(default=None), start: datetime | None = Form(default=None), end: datetime | None = Form(default=None), desc: UploadFile | None = File(default=None)):

    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if file is None:
        config.update(db, name)
    else:
        config.update(db, name, file)
    return config

@admin.post("/problem/delete/{id}")
async def delete_problem(*, db: Session = Depends(get_db), id: UUID):
    config = Config.get(db, id)
    if config is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    config.delete(db)
    return True

#* has to be executed after all route defns
router.include_router(admin)