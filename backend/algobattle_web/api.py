"Module specifying the json api actions."
from datetime import datetime, timedelta
from email.message import EmailMessage
from enum import Enum, StrEnum
from os import environ
from smtplib import SMTP
from typing import Annotated, Any, Callable, Literal, Self, TypeVar
from uuid import UUID
from urllib.parse import quote
from annotated_types import Interval

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, Form, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from pydantic import ByteSize, Field, WithJsonSchema, TypeAdapter

from algobattle.util import Role
from algobattle_web import schemas
from algobattle_web.models import (
    File as DbFile,
    ProblemPageData,
    ResultParticipant,
    ServerSettings,
    TeamSettings,
    UserSettings,
    encode,
    Session,
    ID,
    Tournament,
    Report,
    MatchResult,
    Problem,
    Program,
    ScheduledMatch,
    Team,
    User,
)
from algobattle_web.util import (
    EmailConfig,
    EnvConfig,
    MatchStatus,
    SessionLocal,
    ValueTaken,
    unwrap,
    BaseSchema,
)
from algobattle_web.dependencies import (
    CurrUser,
    Database,
    LoggedIn,
    check_if_admin,
    get_db,
)

__all__ = ("router", "admin")
T = TypeVar("T")


class Remove(Enum):
    remove = "remove"
    _dummy = "_dummy"

    @classmethod
    def convert(cls, value: Self | T) -> T | None:
        if isinstance(value, cls):
            return None
        else:
            return value


class EditAction(Enum):
    add = "add"
    remove = "remove"


str32 = Annotated[str, Body(max_length=32)]
str64 = Annotated[str, Body(max_length=64)]
str128 = Annotated[str, Body(max_length=128)]
str256 = Annotated[str, Body(max_length=256)]
InForm = Annotated[T, Form()]
InBody = Annotated[T, Body()]
SQL_LIMIT = 50


class SchemaRoute(APIRoute):
    """Route that defaults to using the `Schema` entry of the returned object as a response_model."""

    def __init__(
        self, path: str, endpoint: Callable[..., Any], *, response_model: Any = Default(None), **kwargs: Any
    ) -> None:
        if isinstance(response_model, DefaultPlaceholder):
            return_annotation = get_typed_return_annotation(endpoint)
            if hasattr(return_annotation, "Schema"):
                response_model = return_annotation.Schema
        super().__init__(path, endpoint, response_model=response_model, **kwargs)


router = APIRouter(prefix="/api", route_class=SchemaRoute)
admin = APIRouter(prefix="/admin", dependencies=[Depends(check_if_admin)], route_class=SchemaRoute)


# *******************************************************************************
# * General
# *******************************************************************************


@router.get("/files/{id}", tags=["files"])
def get_file(db: Database, *, id: ID) -> FileResponse:
    file = unwrap(db.get(DbFile, id))
    return FileResponse(
        file.path,
        status_code=200 if file.path.exists() else 404,
        filename=file.filename,
        content_disposition_type="inline" if file.media_type == "application/pdf" else "attachment",
        media_type=file.media_type,
    )


# *******************************************************************************
# * User
# *******************************************************************************


class UserSearch(BaseSchema):
    users: dict[ID, schemas.User]
    teams: dict[ID, schemas.Team]
    total: int


@admin.get("/user", tags=["user"])
def search_users(
    *,
    db: Database,
    ids: list[UUID] = [],
    name: str | None = None,
    email: str | None = None,
    is_admin: bool | None = None,
    tournament: ID | None = None,
    team: ID | None = None,
    offset: int = 0,
    exact_search: bool = False,
) -> UserSearch:
    filters: list[Any] = []
    if ids:
        filters.append(User.id.in_(ids))
    if name is not None:
        if exact_search:
            filters.append(User.name == name)
        else:
            filters.append(User.name.contains(name, autoescape=True))
    if email is not None:
        if exact_search:
            filters.append(User.email == name)
        else:
            filters.append(User.email.contains(email, autoescape=True))
    if is_admin is not None:
        filters.append(User.is_admin == is_admin)
    if tournament is not None:
        filters.append(User.teams.any(Team.tournament_id == tournament))
    if team is not None:
        filters.append(User.teams.any(Team.id == team))
    users = (
        db.scalars(
            select(User).where(*filters).order_by(User.is_admin.desc(), User.name.asc()).limit(SQL_LIMIT).offset(offset)
        )
        .unique()
        .all()
    )
    user_count = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    teams = [team for user in users for team in user.teams]
    return UserSearch(
        users=encode(users),
        teams=encode(teams),
        total=user_count,
    )


class CreateUser(BaseSchema):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    is_admin: bool = False
    teams: list[ID] = []


@admin.post("/user", tags=["user"])
def create_user(*, db: Session = Depends(get_db), user: CreateUser) -> User:
    _teams = [unwrap(db.get(Team, id)) for id in user.teams]
    if db.scalars(select(User).filter(User.email == user.email)).unique().first() is not None:
        raise ValueTaken("email", user.email)
    new = User(email=user.email, name=user.name, is_admin=user.is_admin, teams=_teams)
    if new.is_admin:
        new.settings.selected_tournament = db.scalars(select(Tournament).order_by(Tournament.time.desc())).first()
    elif new.teams:
        new.settings.selected_team = new.teams[0]

    db.add(new)
    db.commit()
    return new


class EditUser(BaseSchema):
    name: str | None = Field(None, min_length=1)
    email: str | None = Field(None, min_length=1)
    is_admin: bool | None = None
    teams: dict[ID, EditAction] = {}


@admin.patch("/user/{id}", tags=["user"])
def edit_user(*, db: Session = Depends(get_db), id: ID, edit: EditUser) -> User:
    user = unwrap(User.get(db, id))

    for key, val in edit.model_dump(exclude_unset=True).items():
        if key != "teams":
            setattr(user, key, val)
    for id, action in edit.teams.items():
        team = unwrap(db.get(Team, id))
        match action:
            case EditAction.add if team not in user.teams:
                user.teams.append(team)
            case EditAction.remove if team in user.teams:
                if user.settings.selected_team == team:
                    user.settings.selected_team = None
                user.teams.remove(team)
            case _:
                pass

    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("email", user.email, id) from e
    return user


@admin.delete("/user/{id}", tags=["user"])
def delete_user(*, db: Session = Depends(get_db), id: ID) -> bool:
    user = unwrap(User.get(db, id))
    db.delete(user)
    db.commit()
    return True


class LoginInfo(BaseSchema):
    user: schemas.UserLogin | None
    team: schemas.Team | Literal["admin"] | None
    tournament: schemas.Tournament | None


@router.get("/user/login", tags=["user"], name="getLogin", response_model=LoginInfo)
def get_self(*, db: Database, login: LoggedIn) -> LoggedIn:
    if login.user is not None:
        if login.user.is_admin and login.user.settings.selected_tournament is None:
            login.user.settings.selected_tournament = db.scalars(
                select(Tournament).order_by(Tournament.time.desc())
            ).first()
        if login.team is None and login.user.teams:
            login.user.settings.selected_team = login.user.teams[0]
        db.commit()
    return login


@router.post("/user/login", tags=["user"])
def login(*, db: Database, email: str = Body(), target_url: InBody[str], tasks: BackgroundTasks) -> None:
    user = User.get(db, email)
    if user is not None:
        tasks.add_task(send_login_email, user.id, target_url)


def send_login_email(user_id: UUID, target_url: str) -> None:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if not user:
            return
        token = user.login_token(db)
        url = str(EnvConfig.get().base_url) + target_url + f"?login_token={token}"
        if environ.get("DEV"):
            print(f"sending email to {user.email}: {url}")
            return
        config = ServerSettings.get(db).email_config
        msg = EmailMessage()
        msg["Subject"] = "Algobattle login"
        msg["From"] = config.address
        msg["To"] = user.email
        msg.set_content(url)

        server = SMTP(config.server, config.port)
        server.ehlo()
        server.starttls()
        server.login(config.username, config.password)
        server.sendmail(config.username, user.email, msg.as_string())
        server.close()


class TokenData(BaseSchema):
    token: str
    expires: datetime


@router.get("/user/token/{login_token}", tags=["user"])
def get_token(*, db: Database, login_token: str) -> TokenData:
    user = User.decode_login_token(db, login_token)
    return TokenData(token=user.cookie(db), expires=datetime.now() + timedelta(weeks=4))


# *******************************************************************************
# * Settings
# *******************************************************************************


@router.get("/settings/user", tags=["settings"], name="getUser")
def get_user_settings(*, db: Database, user: CurrUser) -> UserSettings:
    if user is None:
        raise HTTPException(404, "Not logged in")
    return user.settings


@router.patch("/settings/user", tags=["settings"], name="editUser")
def edit_user_settings(
    *,
    db: Database,
    user: CurrUser,
    email: InBody[str | None] = None,
    team: InBody[ID | Literal["admin"] | None] = None,
    tournament: InBody[ID | None] = None,
) -> None:
    if user is None:
        raise HTTPException(400, "Not logged in")
    if email is not None and email != user.email:
        if not ServerSettings.get(db).user_change_email:
            raise HTTPException(400, "Users cannot change their own email")
        if db.scalar(select(User).where(User.email == email, User.id != user.id)):
            raise ValueTaken("email", email)
        user.email = email
    if team == "admin":
        if not user.is_admin:
            raise HTTPException(400, "User is not an admin")
        user.settings.selected_team = None
    elif team is not None:
        if not any(team == t.id for t in user.teams):
            raise HTTPException(400, "User is not in the selected team")
        user.settings.selected_team_id = team
    if tournament is not None:
        if not user.is_admin:
            raise HTTPException(400, "User is not an admin")
        user.settings.selected_tournament_id = tournament
    db.commit()


@router.get("/settings/team", tags=["settings"], name="getTeam")
def get_team_settings(*, db: Database, login: LoggedIn) -> TeamSettings:
    team = login.team
    if not isinstance(team, Team):
        raise HTTPException(400, "User has not selected a team")
    return team.settings


@router.patch("/settings/team", tags=["settings"], name="editTeam")
def edit_team_settings(*, db: Database, login: LoggedIn, name: InBody[str32 | None] = None) -> None:
    team = login.team
    if not isinstance(team, Team):
        raise HTTPException(400, "User has not selected a team")
    if name is not None and name != team.name:
        if not ServerSettings.get(db).team_change_name:
            raise HTTPException(400, "Teams cannot change their own name")
        if db.scalar(
            select(Team).where(Team.tournament_id == team.tournament_id, Team.name == name, Team.id != team.id)
        ):
            raise ValueTaken("name", name)
        team.name = name
    db.commit()


@router.get("/settings/server", tags=["settings"], name="getServer")
def get_server_settings(*, db: Database, login: LoggedIn) -> schemas.ServerSettings | schemas.AdminServerSettings:
    if login.team == "admin":
        return schemas.AdminServerSettings.model_validate(ServerSettings.get(db))
    else:
        return schemas.ServerSettings.model_validate(ServerSettings.get(db))


@admin.patch("/settings/server", tags=["settings"], name="editServer")
def edit_server_settings(
    *,
    db: Database,
    user_change_email: InBody[bool | None] = None,
    team_change_name: InBody[bool | None],
    email_config: InBody[EmailConfig | None] = None,
    upload_file_limit: InBody[
        Annotated[ByteSize, Interval(ge=0, le=2_000_000_000), WithJsonSchema(TypeAdapter(str).json_schema())] | None
    ] = None,
) -> None:
    settings = ServerSettings.get(db)
    if user_change_email is not None:
        settings.user_change_email = user_change_email
    if team_change_name is not None:
        settings.team_change_name = team_change_name
    if email_config is not None:
        settings.email_config = email_config
    if upload_file_limit is not None:
        settings.upload_file_limit = upload_file_limit
    db.commit()


@router.get("/settings/home", tags=["settings"])
def home(db: Database) -> str | None:
    return ServerSettings.get(db).home_page_compiled


# *******************************************************************************
# * Tournament
# *******************************************************************************


@router.get("/tournament", tags=["tournament"], name="get")
def all_tournaments(
    *, db: Database, login: LoggedIn, name: str | None = None, id: ID | None = None
) -> dict[ID, schemas.Tournament]:
    filters = []
    if name:
        filters.append(Tournament.name == name)
    if id:
        filters.append(Tournament.id == id)
    tournaments = db.scalars(select(Tournament).where(*filters, Tournament.visible_sql(login.team))).all()
    return encode(tournaments)


@admin.post("/tournament", tags=["tournament"], name="create")
def create_tournament(*, db: Database, name: str32) -> Tournament:
    if db.scalars(select(Tournament).filter(Tournament.name == name)).first() is not None:
        raise ValueTaken("name", name)
    tournament = Tournament(name=name)
    db.add(tournament)
    db.commit()
    return tournament


@admin.patch("/tournament/{id}", tags=["tournament"], name="edit")
def edit_tournament(*, db: Database, id: ID, name: str32) -> Tournament:
    tournament = unwrap(Tournament.get(db, id))
    if db.scalar(select(Tournament).where(Tournament.name == name, Tournament.id != id)) is not None:
        raise ValueTaken("name", tournament.name)
    tournament.name = name
    db.commit()
    return tournament


@admin.delete("/tournament/{id}", tags=["tournament"], name="delete")
def delete_tournament(*, db: Database, id: ID) -> None:
    tournament = unwrap(Tournament.get(db, id))
    db.delete(tournament)
    db.commit()


# *******************************************************************************
# * Team
# *******************************************************************************


class TeamSearch(BaseSchema):
    total: int
    teams: dict[ID, schemas.Team]
    users: dict[ID, schemas.User]


@admin.get("/team", tags=["team"], name="get")
def get_teams(
    *,
    db: Database,
    ids: list[ID] = [],
    name: str | None = None,
    tournament: ID | None = None,
    offset: int = 0,
) -> TeamSearch:
    filters = []
    if ids:
        filters.append(Team.id.in_(ids))
    if name is not None:
        filters.append(Team.name.contains(name, autoescape=True))
    if tournament is not None:
        filters.append(Team.tournament_id == tournament)
    teams = (
        db.scalars(
            select(Team)
            .where(*filters)
            .order_by(Team.tournament_id.asc(), Team.name.asc())
            .limit(SQL_LIMIT)
            .offset(offset)
        )
        .unique()
        .all()
    )
    team_count = db.scalar(select(func.count()).select_from(Team).where(*filters)) or 0
    users = [user for team in teams for user in team.members]
    return TeamSearch(
        total=team_count,
        teams=encode(teams),
        users=encode(users),
    )


@admin.post("/team", tags=["team"], name="create")
def create_team(*, db: Database, name: str32, tournament: InBody[ID], members: InBody[set[ID]]) -> Team:
    tournament_ = unwrap(Tournament.get(db, tournament))
    if name in (t.name for t in tournament_.teams):
        raise ValueTaken("name", name)
    members_ = [unwrap(db.get(User, id)) for id in members]
    team_ = Team(name, tournament_, members_)
    db.add(team_)
    db.commit()
    return team_


@admin.patch("/team/{id}", tags=["team"], name="edit")
def edit_team(
    *,
    db: Database,
    id: ID,
    name: str32 | None = None,
    tournament: InBody[ID | None] = None,
    members: dict[ID, EditAction] = {},
) -> Team:
    team = unwrap(Team.get(db, id))
    if name is not None:
        team.name = name
    if tournament is not None:
        team.tournament_id = tournament
    for id, action in members.items():
        user = unwrap(db.get(User, id))
        match action:
            case EditAction.add if user not in team.members:
                team.members.append(user)
            case EditAction.remove if user in team.members:
                if user.settings.selected_team == team:
                    user.settings.selected_team = None
                team.members.remove(user)
            case _:
                raise ValueError
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", team.name) from e
    return team


@admin.delete("/team/{id}", tags=["team"])
def delete_team(*, db: Database, id: ID):
    team = unwrap(Team.get(db, id))
    db.delete(team)
    db.commit()


# *******************************************************************************
# * Problem
# *******************************************************************************


@router.get("/problem", tags=["problem"], name="get")
def get_problems(
    *,
    db: Database,
    login: LoggedIn,
    ids: list[ID] | None = None,
    name: str | None = None,
    tournament: ID | None = None,
    tournament_name: str | None = None,
) -> dict[ID, schemas.Problem]:
    filters = []
    if tournament:
        filters.append(Problem.tournament_id == tournament)
    if tournament_name:
        filters.append(Problem.tournament.has(Tournament.name == tournament_name))
    if ids:
        filters.append(Problem.id.in_(ids))
    if name:
        filters.append(Problem.name == name)
    problems = db.scalars(select(Problem).where(*filters, Problem.visible_sql(login.team))).unique().all()
    return encode(problems)


@router.get("/problem/pagedata", tags=["problem"], name="pageData")
def get_problem_page_data(*, db: Database, login: LoggedIn, id: ID) -> ProblemPageData | None:
    prob = db.scalars(select(Problem).where(Problem.id == id, Problem.visible_sql(login.team))).first()
    if prob is None:
        raise ValueError
    return prob.page_data


@admin.post("/problem", tags=["problem"], name="create")
def create_problem(
    *,
    db: Database,
    problem: UploadFile | UUID,
    name: str = Form(),
    tournament: ID = Form(),
    start: datetime | None = Form(None),
    end: datetime | None = Form(None),
    image: UploadFile | None = None,
    alt_text: str = Form(""),
    description: str = Form(""),
    color: str = Form("#ffffff"),
    background_tasks: BackgroundTasks,
) -> str:
    _tournament = unwrap(db.get(Tournament, tournament))
    _image = DbFile.maybe(image, alt_text=alt_text)
    limit = ServerSettings.get(db).upload_file_limit
    if isinstance(problem, UUID):
        template_prob = unwrap(db.get(Problem, problem))
        file = DbFile.from_file(template_prob.file.path, action="copy")
        page_data = template_prob.page_data
    else:
        if problem.size and problem.size > limit:
            raise ValueError
        file = DbFile.from_file(problem)
        page_data = None
    if db.scalars(select(Problem).where(Problem.name == name, Problem.tournament_id == tournament)).first():
        raise ValueTaken("name", name)
    if image is not None and image.size and image.size > limit:
        raise ValueError

    prob = Problem(
        file=file,
        name=name,
        tournament=_tournament,
        start=start,
        end=end,
        image=_image,
        description=description,
        colour=color,
        page_data=page_data,
    )
    db.add(prob)
    db.commit()
    if page_data is None:
        background_tasks.add_task(prob.compute_page_data)
    return f"/problems/{quote(prob.tournament.name, safe='')}/{quote(prob.name, safe='')}"


@admin.patch("/problem/{id}", tags=["problem"], name="edit")
def edit_problem(
    *,
    db: Database,
    id: ID,
    name: InForm[str | None] = None,
    tournament: InForm[ID | None] = None,
    start: InForm[datetime | Remove | None] = None,
    end: InForm[datetime | Remove | None] = None,
    description: InForm[str | None] = None,
    alt_text: InForm[str | None] = None,
    colour: InForm[str | None] = None,
    file: UploadFile | None = None,
    image: UploadFile | InForm[Remove] | None = None,
    tasks: BackgroundTasks,
) -> Problem:
    problem = unwrap(db.get(Problem, id))
    if name:
        new_tournament = tournament or problem.tournament_id
        if db.scalar(
            select(Problem).where(Problem.name == name, Problem.id != id, Problem.tournament_id == new_tournament)
        ):
            raise ValueTaken("name", name)
        problem.name = name
    if tournament:
        problem.tournament = unwrap(db.get(Tournament, tournament))
    if start is not None:
        problem.start = Remove.convert(start)
    if end is not None:
        problem.end = Remove.convert(end)
    if description is not None:
        problem.description = description
    if alt_text is not None and problem.image is not None:
        problem.image.alt_text = alt_text
    if colour:
        problem.colour = colour
    if file:
        if file.size and ServerSettings.get(db).upload_file_limit < file.size:
            raise ValueError
        problem.file = DbFile.from_file(file)
        tasks.add_task(problem.compute_page_data)
    if image is not None:
        image = Remove.convert(image)
        if image is not None and image.size and ServerSettings.get(db).upload_file_limit < image.size:
            raise ValueError
        problem.image = DbFile.maybe(image)
    db.commit()
    return problem


@admin.delete("/problem/{id}", tags=["problem"], name="delete")
def delete_problem(*, db: Database, id: ID) -> bool:
    problem = unwrap(db.get(Problem, id))
    db.delete(problem)
    db.commit()
    return True


# *******************************************************************************
# * Reports
# *******************************************************************************


@router.put("/report/{problem}/{team}", tags=["report"], name="upload")
def add_report(
    *,
    db: Database,
    login: LoggedIn,
    team: ID,
    problem: ID,
    file: UploadFile,
) -> Report:
    if file.size and ServerSettings.get(db).upload_file_limit < file.size:
        raise ValueError
    problem_model = Problem.get_unwrap(db, problem)
    team_model = Team.get_unwrap(db, team)
    if problem_model.tournament != team_model.tournament:
        raise HTTPException(400, "Selected team and problem are not in the same tournament")
    problem_model.assert_editable(login.team)
    report = db.scalar(select(Report).where(Report.team_id == team, Report.problem_id == problem))
    if report:
        report.file = DbFile.from_file(file)
    else:
        report = Report(team_model, problem_model, DbFile.from_file(file))
        db.add(report)
    db.commit()
    return report


@router.delete("/report/{problem}/{team}", tags=["report"], name="delete")
def delete_report(db: Database, login: LoggedIn, team: ID, problem: ID) -> None:
    if isinstance(login.team, Team) and team != login.team.id:
        raise HTTPException(403)
    report = db.scalar(select(Report).where(Report.team_id == team, Report.problem_id == problem))
    if report is None:
        raise HTTPException(404, "No such report exists")
    db.delete(report)
    db.commit()


class Reports(BaseSchema):
    reports: dict[UUID, schemas.Report]
    teams: dict[ID, schemas.Team]
    total: int


@router.get("/report", tags=["report"], name="get")
def get_reports(
    db: Database, login: LoggedIn, problem: UUID | None = None, team: UUID | None = None, offset: int = 0
) -> Reports:
    filters = [Report.visible_sql(login.team)]
    if problem:
        filters.append(Report.problem_id == problem)
    if team:
        filters.append(Report.team_id == team)

    reports = db.scalars(select(Report).where(*filters).limit(SQL_LIMIT).offset(offset)).unique().all()
    count = db.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    return Reports(reports=encode(reports), teams=encode(report.team for report in reports), total=count)


# *******************************************************************************
# * Program
# *******************************************************************************


class ProgramResults(BaseSchema):
    programs: dict[ID, schemas.Program]
    teams: dict[ID, schemas.Team]
    problems: dict[ID, schemas.Problem]
    total: int


@router.get("/program", tags=["program"], name="get")
def search_program(
    *,
    db: Database,
    login: LoggedIn,
    name: str | None = None,
    team: ID | None = None,
    role: Role | None = None,
    problem: ID | None = None,
    tournament: ID | None = None,
    offset: int = 0,
) -> ProgramResults:
    filters = [Program.visible_sql(login.team)]
    if name is not None:
        filters.append(Program.name.contains(name, autoescape=True))
    if team is not None:
        filters.append(Program.team_id == team)
    if role is not None:
        filters.append(Program.role == role)
    if problem is not None:
        filters.append(Program.problem_id == problem)
    if tournament is not None:
        filters.append(Program.problem.has(Problem.tournament_id == tournament))
    programs = (
        db.scalars(
            select(Program).where(*filters).order_by(Program.creation_time.desc()).limit(SQL_LIMIT).offset(offset)
        )
        .unique()
        .all()
    )
    total_count = db.scalar(select(func.count()).select_from(Program).where(*filters)) or 0
    return ProgramResults(
        programs=encode(programs),
        teams=encode(program.team for program in programs),
        problems=encode(program.problem for program in programs),
        total=total_count,
    )


@router.post("/program", tags=["program"], name="create")
def upload_program(
    *,
    db: Database,
    login: LoggedIn,
    name: str = "",
    role: Role,
    problem: ID,
    file: UploadFile,
) -> Program:
    if file.size and ServerSettings.get(db).upload_file_limit < file.size:
        raise ValueError
    problem_obj = unwrap(db.get(Problem, problem))
    problem_obj.assert_visible(login.team)
    if not isinstance(login.team, Team):
        raise HTTPException(400, "User has not selected a team")
    problem_obj.assert_editable(login.team)
    prog = Program(name, login.team, role, DbFile.from_file(file), problem_obj)
    db.add(prog)
    db.commit()
    return prog


@router.delete("/program/{id}", tags=["program"], name="delete")
def delete_program(*, db: Database, login: LoggedIn, id: ID) -> None:
    program = Program.get_unwrap(db, id)
    program.assert_editable(login.team)
    db.delete(program)
    db.commit()


# *******************************************************************************
# * Match
# *******************************************************************************


class ScheduleInfo(BaseSchema):
    matches: dict[ID, schemas.ScheduledMatch]
    problems: dict[ID, schemas.Problem]


@router.get("/match/schedule", tags=["match"], name="getScheduled")
def scheduled_matches(*, db: Database, login: LoggedIn) -> ScheduleInfo:
    matches = (
        db.scalars(
            select(ScheduledMatch).where(
                ScheduledMatch.problem.has((Problem.tournament == login.tournament) & Problem.visible_sql(login.team))
            )
        )
        .unique()
        .all()
    )
    return ScheduleInfo(matches=encode(matches), problems=encode(match.problem for match in matches))


@admin.post("/match/schedule", tags=["match"], name="createSchedule")
def create_schedule(
    *,
    db: Database,
    name: str32 = "",
    time: datetime,
    problem: ID,
    points: int = 100,
) -> ScheduledMatch:
    problem_ = unwrap(db.get(Problem, problem))
    schedule = ScheduledMatch(time=time, problem=problem_, name=name, points=points)
    db.add(schedule)
    db.commit()
    return schedule


@admin.patch("/match/schedule/{id}", tags=["match"], name="editSchedule")
def edit_schedule(
    *,
    db: Database,
    id: ID,
    name: InBody[str | None] = None,
    time: InBody[datetime | None] = None,
    problem: InBody[ID | None] = None,
    points: InBody[int | None] = None,
) -> ScheduledMatch:
    match = unwrap(db.get(ScheduledMatch, id))
    if name is not None:
        match.name = name
    if problem is not None:
        match.problem = unwrap(db.get(Problem, problem))
    if points is not None:
        match.points = points
    if time is not None:
        match.time = time
    db.commit()
    return match


@admin.delete("/match/schedule/{id}", tags=["match"], name="deleteSchedule")
def delete_schedule(*, db: Database, id: ID) -> bool:
    match = unwrap(db.get(ScheduledMatch, id))
    db.delete(match)
    db.commit()
    return True


class MatchResultData(BaseSchema):
    problems: dict[ID, schemas.Problem]
    results: dict[ID, schemas.MatchResult]
    teams: dict[ID, schemas.Team]


@router.get("/match/result", tags=["match"], name="getResult")
def results(
    *, db: Database, login: LoggedIn, problem: ID | None = None, tournament: ID | None = None
) -> MatchResultData:
    filters = [MatchResult.problem.has(Problem.visible_sql(login.team))]
    if problem is not None:
        filters.append(MatchResult.problem_id == problem)
    if tournament is not None:
        filters.append(MatchResult.problem.has(Problem.tournament_id == tournament))
    results = db.scalars(select(MatchResult).where(*filters)).all()
    return MatchResultData(
        results=encode(results),
        problems=encode(result.problem for result in results),
        teams=encode(participant.team for result in results for participant in result.participants),
    )


@admin.delete("/match/result/{id}", tags=["match"], name="deleteResults")
def delete_results(*, db: Database, id: ID) -> None:
    result = MatchResult.get_unwrap(db, id)
    db.delete(result)
    db.commit()


@admin.post("/match/result", tags=["match"], name="createResult", response_model=schemas.MatchResult)
def add_result(
    *,
    db: Database,
    status: MatchStatus,
    time: datetime,
    problem: UUID,
    teams: InForm[list[UUID]],
    generators: InForm[list[UUID]],
    solvers: InForm[list[UUID]],
    points: InForm[list[float]],
    logs: UploadFile | None = None,
) -> MatchResult:
    if logs is not None and logs.size and ServerSettings.get(db).upload_file_limit < logs.size:
        raise ValueError
    problem_model = unwrap(db.get(Problem, problem))
    file = DbFile.from_file(logs) if logs else None
    if len(teams) != len(set(teams)):
        raise HTTPException(422, "Each team can can only appear once in each match")
    try:
        participants = {
            ResultParticipant(
                team=Team.get_unwrap(db, team),
                generator=Program.get_unwrap(db, gen),
                solver=Program.get_unwrap(db, sol),
                points=p,
            )
            for team, gen, sol, p in zip(teams, generators, solvers, points, strict=True)
        }
    except ValueError:
        raise HTTPException(422, "Length of participant field infos was not equal")
    db_res = MatchResult(status=status, time=time, problem=problem_model, participants=participants, logs=file)
    db.add(db_res)
    db.commit()
    return db_res


@admin.put("/match/result/{id}", tags=["match"], name="editResult", response_model=schemas.MatchResult)
def update_result(
    db: Database,
    id: UUID,
    time: InForm[datetime],
    problem: InForm[UUID],
    status: InForm[MatchStatus],
    teams: InForm[list[UUID]],
    generators: InForm[list[UUID]],
    solvers: InForm[list[UUID]],
    points: InForm[list[float]],
    logs: UploadFile | UUID | None = None,
) -> MatchResult:
    res = MatchResult.get_unwrap(db, id)
    res.time = time
    res.problem = Problem.get_unwrap(db, problem)
    res.status = status
    if logs is None:
        res.logs = None
    elif isinstance(logs, UUID):
        res.logs = DbFile.get_unwrap(db, logs)
    elif logs.size and ServerSettings.get(db).upload_file_limit < logs.size:
        raise ValueError
    else:
        res.logs = DbFile.from_file(logs)
    try:
        res.participants = {
            ResultParticipant(
                team=Team.get_unwrap(db, team),
                generator=Program.get_unwrap(db, gen),
                solver=Program.get_unwrap(db, sol),
                points=p,
            )
            for team, gen, sol, p in zip(teams, generators, solvers, points, strict=True)
        }
    except ValueError:
        raise HTTPException(422, "Length of participant field infos was not equal")
    db.commit()
    return res


# * has to be executed after all route defns
router.include_router(admin)
