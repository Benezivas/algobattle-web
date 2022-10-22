"Module specifying the json api actions."
from __future__ import annotations
from typing import Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException
from algobattle_web.database import get_db, Session
from algobattle_web.models import Context, Team, User
from algobattle_web.util import BaseSchema, curr_user


def check_if_admin(user: User = Depends(curr_user)):
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

router = APIRouter(prefix="/api", tags=["api"])
admin = APIRouter(tags=["admin"], dependencies=[Depends(check_if_admin)])

#*******************************************************************************
#* User
#*******************************************************************************

class UserSchema(BaseSchema):
    id: UUID
    name: str
    email: str
    is_admin: bool
    teams: list[UserSchema.Team]

    class Team(BaseSchema):
        id: UUID
        name: str
        context: ContextSchema

class CreateUser(BaseSchema):
    name: str
    email: str
    is_admin: bool = False


@admin.post("/user/create", response_model=UserSchema)
async def create_user(*, db: Session = Depends(get_db), user: CreateUser):
    return User.create(db, user.email, user.name, user.is_admin)


class EditUser(BaseSchema):
    id: UUID
    name: str | None = None
    email: str | None = None
    is_admin: bool | None = None

@admin.post("/user/edit", response_model=UserSchema)
async def edit_user(*, db: Session = Depends(get_db), edit: EditUser):
    user = User.get(db, edit.id)
    if user is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    user.update(db, edit.email, edit.name, edit.is_admin)
    return user

class DeleteUser(BaseSchema):
    id: UUID

@admin.post("/user/delete")
async def delete_user(*, db: Session = Depends(get_db), user: DeleteUser):
    user = User.get(db, user.id)
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

class ContextSchema(BaseSchema):
    id: UUID
    name: str

class CreateContext(BaseSchema):
    name: str

@admin.post("/context/create", response_model=ContextSchema)
async def create_context(*, db: Session = Depends(get_db), context: CreateContext):
    return Context.create(db, context.name)

class EditContext(BaseSchema):
    id: UUID
    name: str | None

@admin.post("/context/edit", response_model=ContextSchema)
async def edit_context(*, db: Session = Depends(get_db), edit: EditContext):
    context = Context.get(db, edit.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.update(db, name=edit.name)
    return context

class DeleteContext(BaseSchema):
    id: UUID

@admin.post("/context/delete")
async def delete_context(*, db: Session = Depends(get_db), context: DeleteContext):
    context = Context.get(db, context.id)
    if context is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    context.delete(db)
    return True

#*******************************************************************************
#* Team
#*******************************************************************************

class TeamSchema(BaseSchema):
    id: UUID
    name: str
    context: ContextSchema
    members: list[UserSchema]

class CreateTeam(BaseSchema):
    name: str
    context: UUID | str | ContextSchema

@admin.post("/team/create", response_model=TeamSchema)
async def create_team(*, db: Session = Depends(get_db), team: CreateTeam):
    if isinstance(team.context, ContextSchema):
        team.context = team.context.id
    return Team.create(db, team.name, team.context)

class EditTeam(BaseSchema):
    id: UUID
    name: str | None = None
    context: UUID | str | ContextSchema

@admin.post("/team/edit", response_model=TeamSchema)
async def edit_team(*, db: Session = Depends(get_db), edit: EditTeam):
    team = Team.get(db, edit.id)
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if isinstance(edit.context, ContextSchema):
        edit.context = edit.context.id
    team.update(db, edit.name, edit.context)
    return team

class DeleteTeam(BaseSchema):
    id: UUID

@admin.post("/team/delete")
async def delete_team(*, db: Session = Depends(get_db), team: DeleteTeam):
    team = Team.get(db, team.id)
    if team is None:
        return False
    else:
        team.delete(db)
        return True

class MemberEditTeam(BaseSchema):
    id: UUID
    name: str

@router.post("/team/member_edit", response_model=TeamSchema)
async def member_edit_team(*, db: Session = Depends(get_db), curr: User = Depends(curr_user), edit: MemberEditTeam):
    team = Team.get(db, edit.id)
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)
    if not any(team.id == t.id for t in curr.teams):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    team.update(db, name=edit.name)
    return team

class AddTeamMember(BaseSchema):
    team: UUID
    user: UUID

@admin.post("/team/add_member", response_model=Tuple[TeamSchema, UserSchema])
async def add_team_member(*, db: Session = Depends(get_db), info: AddTeamMember):
    user = User.get(db, info.user)
    team = Team.get(db, info.team)
    if user is None or team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    team.add_member(db, user)
    return team, user


#* has to be executed after all route defns
router.include_router(admin)
UserSchema.Team.update_forward_refs()
UserSchema.update_forward_refs()