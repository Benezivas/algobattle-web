"Module specifying the json api actions."
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Callable, Literal, cast
from uuid import UUID
from zipfile import ZipFile
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Request, status, HTTPException, UploadFile, Form, File, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse, Response
from markdown import markdown
from sqlalchemy import func, select
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
from backend.algobattle_web.config import SERVER_CONFIG
from backend.algobattle_web.models import UserSettings

from backend.algobattle_web.util import Wrapped, send_email


class SchemaRoute(APIRoute):
    """Route that defaults to using the `Schema` entry of the returned object as a response_model."""

    def __init__(self, path: str, endpoint: Callable[..., Any], *, response_model: Any = Default(None), **kwargs) -> None:
        if isinstance(response_model, DefaultPlaceholder):
            return_annotation = get_typed_return_annotation(endpoint)
            if hasattr(return_annotation, "Schema"):
                response_model = return_annotation.Schema
        super().__init__(path, endpoint, response_model=response_model, **kwargs)


router = APIRouter(prefix="/api", route_class=SchemaRoute)
admin = APIRouter(dependencies=[Depends(check_if_admin)], route_class=SchemaRoute)


# *******************************************************************************
# * Files
# *******************************************************************************


@router.get("/files/{id}", tags=["files"])
def get_file(db = Depends(get_db), *, id: ID) -> FileResponse:
    file = unwrap(db.get(DbFile, id))
    return file.response("inline" if file.media_type == "application/pdf" else "attachment")


# *******************************************************************************
# * User
# *******************************************************************************


class UserWithSettings(User.Schema):
    settings: UserSettings.Schema


@router.get("/user/self", tags=["user"], response_model=UserWithSettings)
def get_self(*, user = Depends(curr_user)) -> User:
    return user


@admin.get("/user", tags=["user"], response_model=list[User.Schema])
def get_user(*, db = Depends(get_db), user = Depends(curr_user), users: list[ID] = Body()):
    return db.scalars(
        select(User)
        .where(User.id.in_(users), User.visible_sql(user))
    )


class UserSearch(BaseSchema):
    page: int
    max_page: int
    users: dict[ID, User.Schema]
    teams: dict[ID, Team.Schema]


@admin.get("/user/search", tags=["user"])
def search_users(
    *,
    db = Depends(get_db),
    name: str | None = None,
    email: str | None = None,
    is_admin: bool | None = None,
    context: ID | None = None,
    team: ID | None = None,
    limit: int = 25,
    page: int = 1,
    ) -> UserSearch:
    filters = []
    if name is not None:
        filters.append(User.name.contains(name, autoescape=True))
    if email is not None:
        filters.append(User.email.contains(email, autoescape=True))
    if is_admin is not None:
        filters.append(User.is_admin == is_admin)
    if context is not None:
        filters.append(User.teams.any(Team.context_id == context))
    if team is not None:
        filters.append(User.teams.any(Team.id == team))
    page = max(page - 1, 0)
    users = db.scalars(
        select(User)
        .where(*filters)
        .order_by(User.is_admin.desc(), User.name.asc())
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    user_count = db.scalar(
        select(func.count())
        .select_from(User)
        .where(*filters)
    ) or 0
    teams = {team for user in users for team in user.teams}
    return UserSearch(
        page=page + 1,
        max_page=user_count // limit + 1,
        users=encode(users),
        teams=encode(teams),
    )


class CreateUser(BaseSchema):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    is_admin: bool = False
    teams: list[ID] = []


@admin.post("/user/create", tags=["user"])
def create_user(*, db: Session = Depends(get_db), user: CreateUser) -> User:
    _teams = [unwrap(db.get(Team, id)) for id in user.teams]
    if db.scalars(select(User).filter(User.email == user.email)).unique().first() is not None:
        raise ValueTaken("email", user.email)
    db.commit()
    return User(db=db, email=user.email, name=user.name, is_admin=user.is_admin, teams=_teams)


class EditUser(BaseSchema):
    name: str | None = Field(None, min_length=1)
    email: str | None = Field(None, min_length=1)
    is_admin: bool | None = None
    teams: dict[ID, bool] = {}


@admin.post("/user/{id}/edit", tags=["user"])
def edit_user(*, db: Session = Depends(get_db), id: ID, edit: EditUser) -> User:
    user = unwrap(User.get(db, id))

    for key, val in edit.dict(exclude_unset=True).items():
        if key != "teams":
            setattr(user, key, val)
    for id, add in edit.teams.items():
        team = unwrap(db.get(Team, id))
        if add and team not in user.teams:
            user.teams.append(team)
        elif not add and team in user.teams:
            user.teams.remove(team)
        else:
            raise ValueError
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("email", user.email, id) from e
    return user


@admin.post("/user/{id}/delete", tags=["user"])
def delete_user(*, db: Session = Depends(get_db), id: ID) -> bool:
    user = unwrap(User.get(db, id))
    db.delete(user)
    db.commit()
    return True


class EditSelf(BaseSchema):
    name: str | None = None
    email: str | None = None


@router.post("/user/self/edit", tags=["user"])
def edit_self(*, db: Session = Depends(get_db), user: User = Depends(curr_user), edit: EditSelf) -> User:
    for key, val in edit.dict(exclude_unset=True).items():
        setattr(user, key, val)
    db.commit()
    return user


class EditSettings(BaseSchema):
    selected_team: ID | None = None


@router.post("/user/self/settings", tags=["user"])
def edit_settings(*, db: Session = Depends(get_db), user: User = Depends(curr_user), settings: EditSettings) -> User:
    updates = settings.dict(exclude_unset=True)
    if "selected_team" in updates:
        team = unwrap(Team.get(db, updates["selected_team"]))
        if team not in user.teams:
            raise HTTPException(status.HTTP_400_BAD_REQUEST)
        user.settings.selected_team = team
    db.commit()
    return user


@router.post("/user/login", tags=["user"])
def login(*, db = Depends(get_db), email: str = Body(), target_url: str = Body()) -> None:
    user = unwrap(User.get(db, email))
    token = user.login_token()
    url = SERVER_CONFIG.frontend_base_url + target_url + f"?login_token={token}"
    send_email(email, url)


class TokenData(BaseSchema):
    token: str
    expires: datetime


@router.post("/user/token", tags=["user"])
def get_token(*, db = Depends(get_db), login_token: str) -> TokenData:
    user = User.decode_login_token(db, login_token)
    user.cookie()
    return TokenData(token=user.cookie(), expires=datetime.now() + timedelta(weeks=4))


# *******************************************************************************
# * Context
# *******************************************************************************


@router.post("/context/all", tags=["context"])
def all_contexts(*, db = Depends(get_db), user = Depends(curr_user)) -> dict[ID, Context.Schema]:
    if user.is_admin:
        contexts = db.scalars(
            select(Context)
        ).unique().all()
    else:
        team = user.settings.selected_team
        if team is not None:
            contexts = [team.context]
        else:
            contexts = []
    return encode(contexts)


@router.post("/context", tags=["context"])
def get_contexts(*, db = Depends(get_db), user = Depends(curr_user), ids: list[ID]) -> dict[ID, Context.Schema]:
    contexts = db.scalars(
        select(Context)
        .where(Context.id.in_(ids), Context.visible_sql(user))
    ).unique().all()
    return encode(contexts)


class CreateContext(BaseSchema):
    name: str = Field(min_length=1)


@admin.post("/context/create", tags=["context"])
def create_context(*, db: Session = Depends(get_db), context: CreateContext) -> Context:
    if db.scalars(select(Context).filter(Context.name == context.name)).unique().first() is not None:
        raise ValueTaken("name", context.name)
    _context = Context(db, context.name)
    db.commit()
    return _context


class EditContext(BaseSchema):
    name: str | None = None


@admin.post("/context/{id}/edit", tags=["context"])
def edit_context(*, db: Session = Depends(get_db), id: ID, data: EditContext) -> Context:
    context = unwrap(Context.get(db, id))    
    if data.name is not None:
        context.name = data.name
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", context.name) from e
    return context


@admin.post("/context/{id}/delete", tags=["context"])
def delete_context(*, db: Session = Depends(get_db), id: ID) -> bool:
    context = unwrap(Context.get(db, id))
    db.delete(context)
    db.commit()
    return True


# *******************************************************************************
# * Team
# *******************************************************************************


@router.post("/team", tags=["team"])
def get_teams(*, db = Depends(get_db), user = Depends(curr_user), ids: list[ID]) -> dict[ID, Team.Schema]:
    teams = db.scalars(
        select(Team)
        .where(Team.id.in_(ids), Team.visible_sql(user))
    ).unique().all()
    return encode(teams)


class TeamSearch(BaseSchema):
    page: int
    max_page: int
    teams: dict[ID, Team.Schema]
    users: dict[ID, User.Schema]


@admin.get("/team/search", tags=["team"])
def search_team(
    *,
    db = Depends(get_db),
    name: str | None = None,
    context: ID | None = None,
    limit: int = 25,
    page: int = 1,
    exact_name: bool = False,
    ) -> TeamSearch:
    filters = []
    if name is not None:
        if exact_name:
            filters.append(Team.name == name)
        else:
            filters.append(Team.name.contains(name, autoescape=True))
    if context is not None:
        filters.append(Team.context_id == context)
    page = max(page - 1, 0)
    teams = db.scalars(
        select(Team)
        .where(*filters)
        .order_by(Team.context_id)
        .limit(limit)
        .offset(page * limit)
    ).unique().all()
    team_count = db.scalar(
        select(func.count())
        .select_from(Team)
        .where(*filters)
    ) or 0
    users = [user for team in teams for user in team.members]
    return TeamSearch(
        page=page + 1,
        max_page=team_count // limit + 1,
        teams=encode(teams),
        users=encode(users),
    )


class CreateTeam(BaseSchema):
    name: str = Field(min_length=1)
    context: ID
    members: list[ID]


@admin.post("/team/create", tags=["team"])
def create_team(*, db: Session = Depends(get_db), team: CreateTeam) -> Team:
    context = unwrap(Context.get(db, team.context))
    members = [unwrap(db.get(User, id)) for id in team.members]
    if db.scalars(select(Team).filter(Team.name == team.name, Team.context_id == team.context)).unique().first() is not None:
        raise ValueTaken("name", team.name)
    _team = Team(db, team.name, context, members)
    db.commit()
    return _team


class EditTeam(BaseSchema):
    name: str | None = Field(None, min_length=1)
    context: ID | None = None
    members: dict[ID, Literal["add", "remove"]] = {}


@admin.post("/team/{id}/edit", tags=["team"])
def edit_team(*, db: Session = Depends(get_db), id: ID, edit: EditTeam) -> Team:
    team = unwrap(Team.get(db, id))
    if edit.name is not None:
        team.name = edit.name
    if edit.context is not None:
        team.context_id = edit.context
    for id, action in edit.members.items():
        user = unwrap(db.get(User, id))
        if action =="add" and user not in team.members:
            team.members.append(user)
        elif action == "remove" and user in team.members:
            team.members.remove(user)
        else:
            raise ValueError
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", team.name) from e
    return team


@admin.post("/team/{id}/delete", tags=["team"])
def delete_team(*, db: Session = Depends(get_db), id: ID) -> bool:
    team = unwrap(Team.get(db, id))
    db.delete(team)
    db.commit()
    return True


class MemberEditTeam(BaseSchema):
    name: str | None = None


@router.post("/team/self/edit", tags=["team"])
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


@router.post("/problem", tags=["problem"])
def get_problems(*, db = Depends(get_db), user = Depends(curr_user), ids: list[ID]) -> dict[ID, Problem.Schema]:
    problems = db.scalars(
        select(Problem)
        .where(Problem.id.in_(ids), Problem.visible_sql(user))
    ).unique().all()
    return encode(problems)


@router.post("/problem/all", tags=["problem"])
def all_problems(*, db = Depends(get_db), user = Depends(curr_user), context: ID | None = None) -> dict[ID, Problem.Schema]:
    filters = []
    if context is not None:
        filters.append(Problem.context_id == context)
    problems = db.scalars(
        select(Problem)
        .where(*filters, Problem.visible_sql(user))
    ).unique().all()
    return encode(problems)


class ProblemInfo(BaseSchema):
    problem: Problem.Schema
    context: Context.Schema

@router.get("/problem/{context_name}/{problem_name}", tags=["problem"], response_model=ProblemInfo)
def problem_by_name(*, db = Depends(get_db), user = Depends(curr_user), context_name: str, problem_name: str):
    problem = unwrap(db.scalars(
        select(Problem)
        .where(
            Problem.name == problem_name,
            Problem.context.has(Context.name == context_name),
        )
    ).unique().first())
    problem.assert_visible(user)
    return {"problem": problem, "context": problem.context}


class ProblemMetadata(BaseSchema):
    name: str
    problem_schema: str | None
    solution_schema: str | None

@admin.post("/problem/verify", tags=["problem"], response_model=ProblemMetadata)
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


@admin.get("/problem/{context}/{problem}", tags=["problem"], response_model=Problem.Schema)
def get_problem(*, db = Depends(get_db), context: str, problem: str):
    return unwrap(db.scalars(select(Problem).join(Context).where(Problem.name == problem, Context.name == context)).unique().first())


@admin.post("/problem/create", tags=["problem"])
def create_problem(*, db: Session = Depends(get_db), 
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
        short_description: str = Form(),
        colour: Color = Form(Color("#ffffff")),
    ) -> Wrapped[str]:
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
    db.add(prob)
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", name) from e
    return Wrapped(data=f"/problems/{prob.context.name}/{prob.name}")


class ProblemEdit(BaseSchema):
    name: str | None = None
    context: ID | None = None
    start: datetime | None = None
    end: datetime | None = None
    short_description: str | None = None
    alt: str | None = None
    problem_schema: str | None = None
    solution_schema: str | None = None
    colour: Color | None = None


@admin.post("/problem/{id}/edit", tags=["problem"])
def edit_problem(*, db: Session = Depends(get_db), id: ID, edit: ProblemEdit) -> Problem:
    problem = unwrap(db.get(Problem, id))
    for key, val in edit.dict(exclude_unset=True).items():
        if key == "context":
            context_ = unwrap(db.get(Context, edit.context))
            problem.context = context_
        elif key == "alt":
            if problem.image is None or edit.alt is None:
                continue
            problem.image.alt_text = edit.alt
        elif key == "colour" and edit.colour is not None:
            problem.colour = edit.colour.as_hex()
        else:
            setattr(problem, key, val)

    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", "") from e
    return problem


@admin.post("/problem/{id}/editFile", tags=["problem"])
def edit_problem_file(
    *,
    db = Depends(get_db),
    id: ID,
    name: Literal["file", "config", "description", "image"] = Form(),
    file: UploadFile | None = File(None),
    ) -> Problem:
    problem = unwrap(db.get(Problem, id))
    if file is None and name in ("file", "config"):
        raise HTTPException(400)
    setattr(problem, name, DbFile.maybe(file))
    db.commit()
    return problem


@admin.post("/problem/{id}/delete", tags=["problem"])
def delete_problem(*, db: Session = Depends(get_db), id: ID) -> bool:
    problem = unwrap(db.get(Problem, id))
    db.delete(problem)
    db.commit()
    return True


@router.get("/problem/{id}/download_all", tags=["problem"])
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


@router.post("/problem/description_content", tags=["problem"])
def problem_desc(*, db = Depends(get_db), user = Depends(curr_user), id: ID) -> Wrapped[str | None]:
    problem = unwrap(db.get(Problem, id))
    problem.assert_visible(user)
    if problem.description is None:
        return Wrapped(data=None)
    else:
        try:
            match problem.description.media_type:
                case "text/plain":
                    with problem.description.open("r") as file:
                        return Wrapped(data=f"<p>{file.read()}</p>")
                case "text/html":
                    with problem.description.open("r") as file:
                        return file.read()
                case "text/markdown":
                    with problem.description.open("r") as file:
                        return Wrapped(data=markdown(cast(str, file.read())))
                case _:
                    return Wrapped(data="__DOWNLOAD_BUTTON__")
        except:
            return Wrapped(data="__DOWNLOAD_BUTTON__")


# *******************************************************************************
# * Docs
# *******************************************************************************


@router.post("/documentation/{problem_id}", tags=["docs"], response_model=Documentation.Schema | None)
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


@admin.post("/documentation/{problem_id}/{team_id}", tags=["docs"], response_model=Documentation.Schema | None)
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
    if problem.context != team.context:
        raise HTTPException(400)
    docs = db.scalars(select(Documentation).where(Documentation.team == team, Documentation.problem == problem)).unique().first()
    if docs is None:
        docs = Documentation(db, team, problem, DbFile(file))
    else:
        docs.file = DbFile(file)
    db.commit()
    return docs


@router.post("/documentation/{problem_id}/delete", tags=["docs"])
def delete_own_docs(*, db = Depends(get_db), user = Depends(curr_user), problem_id: ID):
    team = unwrap(user.settings.selected_team)
    delete_docs(db, user, problem_id, team)


@admin.post("/documentation/{problem_id}/{team_id}/delete", tags=["docs"])
def delete_admin_docs(*, db = Depends(get_db), user = Depends(curr_user), problem_id: ID, team_id: ID):
    team = unwrap(db.get(Team, team_id))
    delete_docs(db, user, problem_id, team)


def delete_docs(db: Session, user: User, problem_id: ID, team: Team):
    problem = unwrap(db.get(Problem, problem_id))
    docs = unwrap(db.scalars(select(Documentation).where(Documentation.team == team, Documentation.problem == problem)).unique().first())
    docs.assert_editable(user)
    db.delete(docs)
    db.commit()


class GetDocs(BaseSchema):
    problem: ID | list[ID] | Literal["all"] = "all"
    team: ID | list[ID] | Literal["all"] = "all"


@router.post("/documentation", tags=["docs"])
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


@router.post("/program/create", tags=["program"])
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
    name: str | None = None
    role: Program.Role | None = None
    problem: ID | None = None


#@router.post("/program/{id}/edit", tags=["program"])
def edit_own_program(
    *, db: Session = Depends(get_db), user: User = Depends(curr_user), id: ID, edit: ProgramEdit = Depends(ProgramEdit.from_form())
) -> Program:
    program = unwrap(db.get(Program, id))
    program.assert_editable(user)
    if edit.name is not None:
        program.name = edit.name
    if edit.role is not None:
        program.role = cast(Program.Role, edit.role)
    if edit.problem is not None:
        program.problem_id = edit.problem
    db.commit()
    return program


@admin.post("/program/{id}/user_editable", tags=["program"])
def edit_program(*, db: Session = Depends(get_db), id: ID, user_editable: bool) -> Program:
    program = unwrap(db.get(Program, id))
    program.user_editable = user_editable
    db.commit()
    return program


@router.post("/program/{id}/delete", tags=["program"])
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


@admin.post("/match/schedule/create", tags=["match"])
def create_schedule(*, db: Session = Depends(get_db), data: ScheduledMatchCreate, background_tasks: BackgroundTasks) -> ScheduledMatch:
    problem = unwrap(db.get(Problem, data.problem))
    config = None
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


@admin.post("/match/schedule/{id}/edit", tags=["match"])
def edit_schedule(*, db: Session = Depends(get_db), id: ID, edit: ScheduleEdit) -> ScheduledMatch:
    match = unwrap(db.get(ScheduledMatch, id))
    if present(edit.name):
        match.name = edit.name
    if present(edit.problem):
        match.problem = unwrap(db.get(Problem, edit.problem))
    if present(edit.config):
        match.config = None
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


@admin.post("/match/schedule/{id}/delete", tags=["match"])
def delete_schedule(*, db: Session = Depends(get_db), id: ID) -> bool:
    match = unwrap(db.get(ScheduledMatch, id))
    db.delete(match)
    db.commit()
    return True


@admin.post("/match/result/{id}/delete", tags=["match"])
def delete_result(*, db: Session = Depends(get_db), id: ID) -> bool:
    result = unwrap(db.get(MatchResult, id))
    db.delete(result)
    db.commit()
    return True


# * has to be executed after all route defns
router.include_router(admin)
