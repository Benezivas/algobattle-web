"Module specifying the json api actions."
from datetime import datetime
from io import BytesIO
from typing import Any, Callable, Literal, cast
from uuid import UUID
from zipfile import ZipFile
from urllib.parse import quote

from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, Form, File, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse, Response
from markdown import markdown
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pydantic import Field
from pydantic.color import Color


from algobattle_web.battle import run_match
from algobattle_web.models import (
    File as DbFile,
    MatchParticipant,
    encode,
    get_db,
    Session,
    ID,
    Context,
    Documentation,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
)
from algobattle_web.util import ValueTaken, unwrap, BaseSchema, Missing, missing, present
from algobattle_web.dependencies import curr_user, check_if_admin
from algobattle.util import TempDir
from algobattle.problem import Problem as AlgProblem


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
# * Files
# *******************************************************************************


@router.get("/files/{id}")
def get_file(db = Depends(get_db), *, id: ID) -> FileResponse:
    file = unwrap(db.get(DbFile, id))
    return file.response("inline" if file.media_type == "application/pdf" else "attachment")


# *******************************************************************************
# * User
# *******************************************************************************


@admin.get("/user/search", response_model=list[User.Schema])
def get_users(
    *,
    db = Depends(get_db),
    name: str | None = None,
    email: str | None = None,
    is_admin: bool | None = None,
    context: ID | None = None,
    team: ID | None = None,
    limit: int = 25,
    page: int = 1,
    ):
    filters = []
    where = []
    teams_filters = []
    if name is not None:
        filters.append(User.name.contains(name, autoescape=True))
    if email is not None:
        filters.append(User.email.contains(email, autoescape=True))
    if is_admin is not None:
        filters.append(User.is_admin == is_admin)
    if context is not None:
        _context = unwrap(db.get(Context, context))
        where.append(User.teams.any(Team.context_id == _context.id))
        teams_filters.append(Team.context_id == _context.id)
    if team is not None:
        where.append(User.teams.any(Team.id == team))
    page = max(page - 1, 0)
    users = db.scalars(
        select(User)
        .filter(*filters)
        .where(*where)
        .order_by(User.is_admin.desc())
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    return users


class CreateUser(BaseSchema):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    is_admin: bool = False
    teams: list[ID] = []


@admin.post("/user/create")
def create_user(*, db: Session = Depends(get_db), user: CreateUser) -> User:
    _teams = [unwrap(db.get(Team, id)) for id in user.teams]
    if db.scalars(select(User).filter(User.email == user.email)).unique().first() is not None:
        raise ValueTaken("email", user.email)
    db.commit()
    return User(db=db, email=user.email, name=user.name, is_admin=user.is_admin, teams=_teams)


class EditUser(BaseSchema):
    name: str | Missing = Field(missing, min_length=1)
    email: str | Missing = Field(missing, min_length=1)
    is_admin: bool | Missing = missing
    teams: dict[ID, bool] | Missing = missing


@admin.post("/user/{id}/edit")
def edit_user(*, db: Session = Depends(get_db), id: ID, edit: EditUser) -> User:
    user = unwrap(User.get(db, id))
    edit_email = edit.email if present(edit.email) else user.email
    if db.scalars(select(User).filter(User.email == edit_email, User.id != id)).unique().first() is not None:
        raise ValueTaken("email", user.email, id)

    for key, val in edit.dict(exclude_unset=True).items():
        if key != "teams":
            setattr(user, key, val)
    if present(edit.teams):
        for id, add in edit.teams.items():
            team = unwrap(db.get(Team, id))
            if add and team not in user.teams:
                user.teams.append(team)
            elif not add and team in user.teams:
                user.teams.remove(team)
            else:
                raise ValueError
    db.commit()
    return user


@admin.post("/user/{id}/delete")
def delete_user(*, db: Session = Depends(get_db), id: ID) -> bool:
    user = unwrap(User.get(db, id))
    db.delete(user)
    db.commit()
    return True


class EditSelf(BaseSchema):
    name: str | Missing = missing
    email: str | Missing = missing


@router.post("/user/self/edit")
def edit_self(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: EditSelf) -> User:
    for key, val in edit.dict(exclude_unset=True).items():
        setattr(user, key, val)
    db.commit()
    return user


class EditSettings(BaseSchema):
    selected_team: ID | Missing = missing


@router.post("/user/self/settings")
def edit_settings(*, db: Session = Depends(get_db), user: User = Depends(curr_user), settings: EditSettings) -> User:
    updates = settings.dict(exclude_unset=True)
    if "selected_team" in updates:
        team = unwrap(Team.get(db, updates["selected_team"]))
        if team not in user.teams:
            raise HTTPException(status.HTTP_400_BAD_REQUEST)
        user.settings.selected_team = team
    db.commit()
    return user


# *******************************************************************************
# * Context
# *******************************************************************************


class CreateContext(BaseSchema):
    name: str = Field(min_length=1)


@admin.post("/context/create")
def create_context(*, db: Session = Depends(get_db), context: CreateContext) -> Context:
    if db.scalars(select(Context).filter(Context.name == context.name)).unique().first() is not None:
        raise ValueTaken("name", context.name)
    _context = Context(db, context.name)
    db.commit()
    return _context


class EditContext(BaseSchema):
    name: str | Missing = missing


@admin.post("/context/{id}/edit")
def edit_context(*, db: Session = Depends(get_db), id: ID, data: EditContext) -> Context:
    context = unwrap(Context.get(db, id))
    edit_name = data.name if present(data.name) else context.name
    if db.scalars(select(Context).filter(Context.name == edit_name, Context.id != id)).unique().first() is not None:
        raise ValueTaken("name", context.name)
    if present(data.name):
        context.name = data.name
    db.commit()
    return context


@admin.post("/context/{id}/delete")
def delete_context(*, db: Session = Depends(get_db), id: ID) -> bool:
    context = unwrap(Context.get(db, id))
    db.delete(context)
    db.commit()
    return True


# *******************************************************************************
# * Team
# *******************************************************************************


@router.post("/team")
def get_teams(*, db = Depends(get_db), user = Depends(curr_user), team: ID | list[ID]):
    if isinstance(team, UUID):
        team = [team]
    teams = db.scalars(
        select(Team)
        .where(Team.id.in_(team), Team.visible_sql(user))
    ).unique().all()
    return encode(teams)


@admin.get("/team/search", response_model=list[Team.Schema])
def search_team(
    *,
    db = Depends(get_db),
    name: str | None = None,
    context: ID | None = None,
    limit: int = 25,
    page: int = 1,
    ):
    filters = []
    if name is not None:
        filters.append(Team.name.contains(name, autoescape=True))
    if context is not None:
        unwrap(db.get(Context, context))
        filters.append(Team.context_id == context)
    page = max(page - 1, 0)
    users = db.scalars(
        select(Team)
        .filter(*filters)
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    return users


class CreateTeam(BaseSchema):
    name: str = Field(min_length=1)
    context: ID
    members: list[ID]


@admin.post("/team/create")
def create_team(*, db: Session = Depends(get_db), team: CreateTeam) -> Team:
    context = unwrap(Context.get(db, team.context))
    members = [unwrap(db.get(User, id)) for id in team.members]
    if db.scalars(select(Team).filter(Team.name == team.name, Team.context_id == team.context)).unique().first() is not None:
        raise ValueTaken("name", team.name)
    _team = Team(db, team.name, context, members)
    db.commit()
    return _team


class EditTeam(BaseSchema):
    name: str | Missing = Field(missing, min_length=1)
    context: ID | Missing = missing
    members: dict[ID, bool] | Missing = missing


@admin.post("/team/{id}/edit")
def edit_team(*, db: Session = Depends(get_db), id: ID, edit: EditTeam) -> Team:
    team = unwrap(Team.get(db, id))
    edit_context = edit.context if present(edit.context) else team.context.id
    if db.scalars(select(Team).filter(Team.name == edit.name, Team.context_id == edit_context, Team.id != id)).unique().first() is not None:
        raise ValueTaken("name", team.name)
    if present(edit.name):
        team.name = edit.name
    if present(edit.context):
        team.context_id = edit.context
    if present(edit.members):
        for id, add in edit.members.items():
            user = unwrap(db.get(User, id))
            if add and user not in team.members:
                team.members.append(user)
            elif not add and user in team.members:
                team.members.remove(user)
            else:
                raise ValueError
    db.commit()
    return team


@admin.post("/team/{id}/delete")
def delete_team(*, db: Session = Depends(get_db), id: ID) -> bool:
    team = unwrap(Team.get(db, id))
    db.delete(team)
    db.commit()
    return True


class MemberEditTeam(BaseSchema):
    name: str | None = None


@router.post("/team/self/edit")
def member_edit_team(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: MemberEditTeam) -> Team:
    team = unwrap(user.settings.selected_team)
    team.assert_editable(user)
    if edit.name is not None:
        team.name = edit.name
    db.commit()
    return team


# *******************************************************************************
# * Problem
# *******************************************************************************


class ProblemMetadata(BaseSchema):
    name: str
    problem_schema: str | None
    solution_schema: str | None

@admin.post("/problem/verify", response_model=ProblemMetadata)
def verify_problem(*, db = Depends(get_db), file: UploadFile | None = File(None), problem_id: ID | None = Form(None)):
    if file is None == problem_id is None:
        raise ValueError
    if file is not None:
        with TempDir() as folder:
            with open(folder / "problem.py", "wb+") as _file:
                _file.write(file.file.read())
            try:
                prob = AlgProblem.import_from_path(folder / "problem.py")
            except ValueError as e:
                print(e)
                raise HTTPException(400)
            return ProblemMetadata(name=prob.name, problem_schema=prob.io_schema(), solution_schema=prob.Solution.io_schema())
    else:
        return unwrap(db.get(Problem, problem_id))


@admin.get("/problem/{context}/{problem}", response_model=Problem.Schema)
def get_problem(*, db = Depends(get_db), context: str, problem: str):
    return unwrap(db.scalars(select(Problem).join(Context).where(Problem.name == problem, Context.name == context)).unique().first())


@admin.post("/problem/create")
def add_problem(*, db: Session = Depends(get_db), 
        file: UploadFile | None = File(None),
        problem_id: ID | None = Form(None),
        name: str = Form(),
        description: UploadFile | None = File(None),
        problem_schema: str | None = Form(None),
        solution_schema: str | None = Form(None),
        context: ID = Form(),
        config: UploadFile | None = File(None),
        start: datetime | None = Form(None),
        end: datetime | None = Form(None),
        image: UploadFile | None = File(None),
        alt_text: str = Form(""),
        short_description: str | None = Form(None),
        colour: Color = Form(Color("#ffffff")),
    ) -> str:
    if file is None == problem_id is None:
        raise HTTPException(400)
    if file is not None:
        _file = DbFile(file)
    else:
        template_prob = unwrap(db.get(Problem, problem_id))
        _file = DbFile(template_prob.file)

    if description is not None:
        desc = DbFile(description)
    else:
        desc = None

    _context = unwrap(db.get(Context, context))
    if config is None:
        config = UploadFile("config.toml")

    if image is not None:
        _image = DbFile(image, alt_text=alt_text)
    else:
        _image = None

    prob = Problem(
        db=db,
        file=_file,
        name=name,
        description=desc,
        problem_schema=problem_schema,
        solution_schema=solution_schema,
        context=_context,
        config=DbFile(config),
        start=start,
        end=end,
        image=_image,
        short_description=short_description,
        colour=colour.as_hex(),
    )
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", name) from e
    return f"/problems/{prob.context.name}/{prob.name}"


class ProblemEdit(BaseSchema):
    name: str | Missing = missing
    context: ID | Missing = missing
    file: UploadFile | Missing = missing
    config: UploadFile | Missing = missing
    start: datetime | None | Missing = missing
    end: datetime | None | Missing = missing
    description: UploadFile | Literal["null"] | Missing = missing
    short_description: str | None | Missing = missing
    image: UploadFile | Literal["null"] | Missing = missing
    alt: str | None | Missing = missing
    problem_schema: str | None | Missing = missing
    solution_schema: str | None | Missing = missing
    colour: str | Missing = missing


@admin.post("/problem/{id}/edit")
def edit_problem(*, db: Session = Depends(get_db), id: ID, edit: ProblemEdit = Depends(ProblemEdit.from_form())) -> Problem:
    problem = unwrap(db.get(Problem, id))
    for key in ("name", "start", "end", "short_description", "problem_schema", "solution_schema", "colour"):
        val = getattr(edit, key)
        if present(val):
            setattr(problem, key, val)
    for key in ("file", "config", "description", "image"):
        val = getattr(edit, key)
        if val == "null":
            setattr(problem, key, None)
        elif present(val):
            setattr(problem, key, DbFile(val))
    if problem.image and present(edit.alt):
        problem.image.alt_text = edit.alt

    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", edit.name if present(edit.name) else "") from e
    return problem


@admin.post("/problem/{id}/delete")
def delete_problem(*, db: Session = Depends(get_db), id: ID) -> bool:
    problem = unwrap(db.get(Problem, id))
    db.delete(problem)
    db.commit()
    return True


@router.get("/problem/{id}/download_all")
def download_problem(*, db = Depends(get_db), user = Depends(curr_user), id: ID) -> Response:
    problem = unwrap(db.get(Problem, id))
    problem.assert_visible(user)
    with BytesIO() as file:
        with ZipFile(file, "w") as zipfile:
            zipfile.write(problem.file.path, problem.file.filename)
            if problem.description is not None:
                zipfile.write(problem.description.path, problem.description.filename)
            zipfile.write(problem.config.path, problem.config.filename)
            if problem.problem_schema is not None:
                zipfile.writestr("problem_schema.json", problem.problem_schema)
            if problem.solution_schema is not None:
                zipfile.writestr("solution_schema.json", problem.solution_schema)

        file.seek(0)
        quoted = quote(problem.name)
        if quoted != problem.name:
            disposition = f"attachment; filename*=utf-8''{quoted}.zip"
        else:
            disposition = f'attachment; filename="{quoted}.zip"'
        return Response(file.getvalue(), headers={"content-disposition": disposition}, media_type="application/zip")


@router.get("/problem/{id}/description_content")
def problem_desc(*, db = Depends(get_db), user = Depends(curr_user), id: ID) -> str | None:
    problem = unwrap(db.get(Problem, id))
    problem.assert_visible(user)
    if problem.description is None:
        return None
    else:
        try:
            match problem.description.media_type:
                case "text/plain":
                    with problem.description.open("r") as file:
                        return f"<p>{file.read()}</p>"
                case "text/html":
                    with problem.description.open("r") as file:
                        return file.read()
                case "text/markdown":
                    with problem.description.open("r") as file:
                        return markdown(cast(str, file.read()))
                case _:
                    return "__DOWNLOAD_BUTTON__"
        except:
            return "__DOWNLOAD_BUTTON__"


# *******************************************************************************
# * Docs
# *******************************************************************************


@router.post("/documentation/{problem_id}", response_model=Documentation.Schema | None)
def upload_own_docs(
        *,
        db: Session = Depends(get_db),
        user: User = Depends(curr_user),
        problem_id: ID,
        file: UploadFile = File(),
    ) -> Documentation | None:
    problem = unwrap(db.get(Problem, problem_id))
    team = unwrap(user.settings.selected_team)
    return docs_edit(db, user, problem, team, file)


@admin.post("/documentation/{problem_id}/{team_id}", response_model=Documentation.Schema | None)
def upload_docs(
        *,
        db = Depends(get_db),
        user = Depends(curr_user),
        problem_id: ID,
        team_id: ID,
        file: UploadFile = File(),
    ) -> Documentation | None:
    problem = unwrap(db.get(Problem, problem_id))
    team = unwrap(db.get(Team, team_id))
    return docs_edit(db, user, problem, team, file)


def docs_edit(
        db: Session,
        user: User,
        problem: Problem,
        team: Team,
        file: UploadFile,
    ) -> Documentation | None:
    problem.assert_editable(user)
    docs = db.scalars(select(Documentation).where(Documentation.team == team, Documentation.problem == problem)).unique().first()
    if docs is None:
        docs = Documentation(db, team, problem, DbFile(file))
    else:
        docs.file = DbFile(file)
    db.commit()
    return docs


@router.post("/documentation/{problem_id}/delete")
def delete_own_docs(*, db = Depends(get_db), user = Depends(curr_user), problem_id: ID):
    team = unwrap(user.settings.selected_team)
    delete_docs(db, user, problem_id, team)


@admin.post("/documentation/{problem_id}/{team_id}/delete")
def delete_admin_docs(*, db = Depends(get_db), user = Depends(curr_user), problem_id: ID, team_id: ID):
    team = unwrap(db.get(Team, team_id))
    delete_docs(db, user, problem_id, team)


def delete_docs(db: Session, user: User, problem_id: ID, team: Team):
    problem = unwrap(db.get(Problem, problem_id))
    docs = unwrap(db.scalars(select(Documentation).where(Documentation.team == team, Documentation.problem == problem)).unique().first())
    docs.assert_editable(user)
    db.delete(docs)


class GetDocs(BaseSchema):
    problem: ID | list[ID] | Literal["all"] = "all"
    team: ID | list[ID] | Literal["all"] = "all"


@router.post("/documentation")
def get_docs(*, db = Depends(get_db), user = Depends(curr_user), data: GetDocs, page: int = 0, limit: int = 25) -> dict[ID, Documentation.Schema]:
    filters = [Documentation.visible_sql(user)]
    if isinstance(data.problem, UUID):
        filters.append(Documentation.problem_id == data.problem)
    elif isinstance(data.problem, list):
        filters.append(Documentation.problem_id.in_(data.problem))
    if isinstance(data.team, UUID):
        filters.append(Documentation.team_id == data.team)
    elif isinstance(data.team, list):
        filters.append(Documentation.team_id.in_(data.team))
    elif not user.is_admin:
        team = unwrap(user.settings.selected_team)
        filters.append(Documentation.team == team)

    docs = db.scalars(
        select(Documentation)
        .where(*filters)
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    return encode(docs)


# *******************************************************************************
# * Program
# *******************************************************************************


class ProgramCreate(BaseSchema):
    name: str
    role: Program.Role
    file: UploadFile
    problem: ID


@router.post("/program/create")
def add_program(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    data: ProgramCreate = Depends(ProgramCreate.from_form()),
) -> Program:
    team = unwrap(user.settings.selected_team)
    problem = unwrap(db.get(Problem, data.problem))
    problem.assert_visible(user)
    file = DbFile(data.file)
    prog = Program(db, data.name, team, data.role, file, problem)
    db.commit()
    return prog


class ProgramEdit(BaseSchema):
    name: str | Missing = missing
    role: Program.Role | Missing = missing
    problem: ID | Missing = missing


@router.post("/program/{id}/edit")
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
    db.commit()
    return program


@admin.post("/program/{id}/user_editable")
def edit_program(*, db: Session = Depends(get_db), id: ID, user_editable: bool) -> Program:
    program = unwrap(db.get(Program, id))
    program.user_editable = user_editable
    db.commit()
    return program


@router.post("/program/{id}/delete")
def delete_program(*, db: Session = Depends(get_db), user = Depends(curr_user), id: ID) -> bool:
    program = unwrap(db.get(Program, id))
    program.assert_editable(user)
    db.delete(program)
    db.commit()
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
def create_schedule(*, db: Session = Depends(get_db), data: ScheduledMatchCreate, background_tasks: BackgroundTasks) -> ScheduledMatch:
    problem = unwrap(db.get(Problem, data.problem))
    config = unwrap(db.get(Config, data.config)) if data.config is not None else None
    schedule = ScheduledMatch(db, data.time, problem, config, data.name, data.points)
    for team_id, info in data.participants.items():
        team = unwrap(db.get(Team, team_id))
        gen = unwrap(db.get(Program, info.generator)) if info.generator is not None else None
        sol = unwrap(db.get(Program, info.solver)) if info.solver is not None else None
        schedule.participants.add(MatchParticipant(db, schedule, team, gen, sol))

    #! Prototype
    if schedule.time <= datetime.now():
        background_tasks.add_task(run_match, db, schedule)
    db.commit()
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
def edit_schedule(*, db: Session = Depends(get_db), id: ID, edit: ScheduleEdit) -> ScheduledMatch:
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
    db.commit()
    return match


@admin.post("/match/schedule/{id}/delete")
def delete_schedule(*, db: Session = Depends(get_db), id: ID) -> bool:
    match = unwrap(db.get(ScheduledMatch, id))
    db.delete(match)
    db.commit()
    return True


@admin.post("/match/result/{id}/delete")
def delete_result(*, db: Session = Depends(get_db), id: ID) -> bool:
    result = unwrap(db.get(MatchResult, id))
    db.delete(result)
    db.commit()
    return True


# * has to be executed after all route defns
router.include_router(admin)