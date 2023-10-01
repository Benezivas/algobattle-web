"Module specifying the json api actions."
from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Any, Callable, Literal, TypeVar
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, Form, File, BackgroundTasks
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_typed_return_annotation
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from pydantic import Field

from algobattle.util import Role
from algobattle_web import schemas
from algobattle_web.models import (
    File as DbFile,
    ProblemPageData,
    ResultParticipant,
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
    MatchStatus,
    ValueTaken,
    unwrap,
    BaseSchema,
    send_email,
    ServerConfig,
)
from algobattle_web.dependencies import (
    CurrTournament,
    CurrUser,
    CurrUserMaybe,
    Database,
    TeamIfAdmin,
    curr_user,
    check_if_admin,
    get_db,
)
from pydantic_extra_types.color import Color

__all__ = ("router", "admin")

T = TypeVar("T")
InForm = Annotated[T, Form()]


class EditAction(Enum):
    add = "add"
    remove = "remove"


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
# * Files
# *******************************************************************************


@router.get("/files/{id}", tags=["files"])
def get_file(db: Database, *, id: ID) -> FileResponse:
    file = unwrap(db.get(DbFile, id))
    return file.response("inline" if file.media_type == "application/pdf" else "attachment")


# *******************************************************************************
# * User
# *******************************************************************************


@router.get("/user/login", tags=["user"], name="getLogin", response_model=schemas.UserLogin | None)
def get_self(*, user: CurrUserMaybe) -> User | None:
    return user


class UserSearch(BaseSchema):
    page: int
    max_page: int
    users: dict[ID, schemas.User]
    teams: dict[ID, schemas.Team]


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
    limit: int = 25,
    page: int = 1,
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
    page = max(page - 1, 0)
    users = (
        db.scalars(
            select(User)
            .where(*filters)
            .order_by(User.is_admin.desc(), User.name.asc())
            .limit(limit)
            .offset(page * limit)
        )
        .unique()
        .all()
    )
    user_count = db.scalar(select(func.count()).select_from(User).where(*filters)) or 0
    teams = [team for user in users for team in user.teams]
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


@admin.post("/user", tags=["user"])
def create_user(*, db: Session = Depends(get_db), user: CreateUser) -> User:
    _teams = [unwrap(db.get(Team, id)) for id in user.teams]
    if db.scalars(select(User).filter(User.email == user.email)).unique().first() is not None:
        raise ValueTaken("email", user.email)
    new = User(email=user.email, name=user.name, is_admin=user.is_admin, teams=_teams)
    db.add(new)
    db.commit()
    return new


class EditUser(BaseSchema):
    name: str | None = Field(None, min_length=1)
    email: str | None = Field(None, min_length=1)
    is_admin: bool | None = None
    teams: dict[ID, EditAction] = {}


@admin.patch("/user", tags=["user"])
def edit_user(*, db: Session = Depends(get_db), id: ID, edit: EditUser) -> User:
    user = unwrap(User.get(db, id))

    for key, val in edit.model_dump(exclude_unset=True).items():
        if key != "teams":
            setattr(user, key, val)
    for id, action in edit.teams.items():
        team = unwrap(db.get(Team, id))
        match action:
            case EditAction.add:
                if team not in user.teams:
                    user.teams.append(team)
            case EditAction.remove:
                if team in user.teams:
                    user.teams.remove(team)
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("email", user.email, id) from e
    return user


@admin.delete("/user", tags=["user"])
def delete_user(*, db: Session = Depends(get_db), id: ID) -> bool:
    user = unwrap(User.get(db, id))
    db.delete(user)
    db.commit()
    return True


@router.patch("/user/settings", tags=["user"], response_model=schemas.UserLogin)
def settings(*, db: Database, user: CurrUser, email: str | None = None, team: ID | Literal["admin"] | None = None) -> User:
    if email is not None:
        user.email = email
    if team == "admin":
        if not user.is_admin:
            raise HTTPException(400, "User is not an admin")
        user.settings.selected_team = None
    elif team is not None:
        if not any(team == t.id for t in user.teams):
            raise HTTPException(400, "User is not in the selected team")
        user.settings.selected_team_id = team
    db.commit()
    return user


@router.post("/user/login", tags=["user"])
def login(*, db: Database, email: str = Body(), target_url: str = Body(), tasks: BackgroundTasks) -> None:
    user = User.get(db, email)
    if user is None:
        return
    token = user.login_token()
    url = str(ServerConfig.obj.frontend_base_url) + target_url + f"?login_token={token}"
    tasks.add_task(send_email, email, url)


class TokenData(BaseSchema):
    token: str
    expires: datetime


@router.post("/user/token", tags=["user"])
def get_token(*, db: Database, login_token: str) -> TokenData:
    user = User.decode_login_token(db, login_token)
    user.cookie()
    return TokenData(token=user.cookie(), expires=datetime.now() + timedelta(weeks=4))


# *******************************************************************************
# * Tournament
# *******************************************************************************


@router.post("/tournament/all", tags=["tournament"])
def all_tournaments(*, db: Database, user: CurrUser) -> dict[ID, schemas.Tournament]:
    if user.is_admin:
        tournaments = db.scalars(select(Tournament)).unique().all()
    else:
        team = user.settings.selected_team
        if team is not None:
            tournaments = [team.tournament]
        else:
            tournaments = []
    return encode(tournaments)


@router.post("/tournament", tags=["tournament"])
def get_tournaments(*, db: Database, user: CurrUser, ids: list[ID]) -> dict[ID, schemas.Tournament]:
    tournaments = (
        db.scalars(select(Tournament).where(Tournament.id.in_(ids), Tournament.visible_sql(user))).unique().all()
    )
    return encode(tournaments)


class CreateTournament(BaseSchema):
    name: str = Field(min_length=1)


@admin.post("/tournament/create", tags=["tournament"])
def create_tournament(*, db: Session = Depends(get_db), tournament: CreateTournament) -> Tournament:
    if db.scalars(select(Tournament).filter(Tournament.name == tournament.name)).unique().first() is not None:
        raise ValueTaken("name", tournament.name)
    _tournament = Tournament(tournament.name)
    db.add(_tournament)
    db.commit()
    return _tournament


class EditTournament(BaseSchema):
    name: str | None = None


@admin.post("/tournament/{id}/edit", tags=["tournament"])
def edit_tournament(*, db: Session = Depends(get_db), id: ID, data: EditTournament) -> Tournament:
    tournament = unwrap(Tournament.get(db, id))
    if data.name is not None:
        tournament.name = data.name
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", tournament.name) from e
    return tournament


@admin.post("/tournament/{id}/delete", tags=["tournament"])
def delete_tournament(*, db: Session = Depends(get_db), id: ID) -> bool:
    tournament = unwrap(Tournament.get(db, id))
    db.delete(tournament)
    db.commit()
    return True


# *******************************************************************************
# * Team
# *******************************************************************************


@router.post("/team", tags=["team"])
def get_teams(*, db: Database, user: CurrUser, ids: list[ID]) -> dict[ID, schemas.Team]:
    teams = db.scalars(select(Team).where(Team.id.in_(ids), Team.visible_sql(user))).unique().all()
    return encode(teams)


class TeamSearch(BaseSchema):
    page: int
    max_page: int
    teams: dict[ID, schemas.Team]
    users: dict[ID, schemas.User]


@admin.get("/team/search", tags=["team"])
def search_team(
    *,
    db: Database,
    name: str | None = None,
    tournament: ID | None = None,
    limit: int = 25,
    page: int = 1,
    exact_name: bool = False,
) -> TeamSearch:
    filters: list[Any] = []
    if name is not None:
        if exact_name:
            filters.append(Team.name == name)
        else:
            filters.append(Team.name.contains(name, autoescape=True))
    if tournament is not None:
        filters.append(Team.tournament_id == tournament)
    page = max(page - 1, 0)
    teams = (
        db.scalars(
            select(Team)
            .where(*filters)
            .order_by(Team.tournament_id.asc(), Team.name.asc())
            .limit(limit)
            .offset(page * limit)
        )
        .unique()
        .all()
    )
    team_count = db.scalar(select(func.count()).select_from(Team).where(*filters)) or 0
    users = [user for team in teams for user in team.members]
    return TeamSearch(
        page=page + 1,
        max_page=team_count // limit + 1,
        teams=encode(teams),
        users=encode(users),
    )


class CreateTeam(BaseSchema):
    name: str = Field(min_length=1)
    tournament: ID
    members: set[ID]


@admin.post("/team/create", tags=["team"])
def create_team(*, db: Session = Depends(get_db), team: CreateTeam) -> Team:
    tournament = unwrap(Tournament.get(db, team.tournament))
    members = [unwrap(db.get(User, id)) for id in team.members]
    _team = Team(team.name, tournament, members)
    try:
        db.add(_team)
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", team.name) from e
    return _team


class EditTeam(BaseSchema):
    name: str | None = Field(None, min_length=1)
    tournament: ID | None = None
    members: dict[ID, EditAction] = {}


@admin.post("/team/{id}/edit", tags=["team"])
def edit_team(*, db: Session = Depends(get_db), id: ID, edit: EditTeam) -> Team:
    team = unwrap(Team.get(db, id))
    if edit.name is not None:
        team.name = edit.name
    if edit.tournament is not None:
        team.tournament_id = edit.tournament
    for id, action in edit.members.items():
        user = unwrap(db.get(User, id))
        match action, user in team.members:
            case [EditAction.add, False]:
                team.members.append(user)
            case [EditAction.remove, True]:
                team.members.remove(user)
            case [_, _]:
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


@router.get("/problem", tags=["problem"], name="get")
def get_problems(
    *, db: Database, user: CurrUser, ids: list[ID] | None = None, tournament: ID | str | None = None, name: str | None = None
) -> dict[ID, schemas.Problem]:
    filters = []
    if ids:
        filters.append(Problem.id.in_(ids))
    if isinstance(tournament, UUID):
        filters.append(Problem.tournament_id == tournament)
    elif isinstance(tournament, str):
        filters.append(Problem.tournament.has(Tournament.name == tournament))
    if name:
        filters.append(Problem.name == name)
    problems = db.scalars(select(Problem).where(*filters, Problem.visible_sql(user))).unique().all()
    return encode(problems)


@router.get("/problem/pagedata", tags=["problem"], name="pageData")
def get_problem_page_data(*, db: Database, user: CurrUser, id: ID) -> ProblemPageData | None:
    prob = db.scalars(select(Problem).where(Problem.id == id, Problem.visible_sql(user))).first()
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
    short_description: str = Form(""),
    colour: Color = Form(Color("#ffffff")),
    background_tasks: BackgroundTasks,
) -> str:
    _tournament = unwrap(db.get(Tournament, tournament))
    _image = DbFile.maybe(image, alt_text=alt_text)
    if isinstance(problem, UUID):
        template_prob = unwrap(db.get(Problem, problem))
        file = DbFile.from_file(template_prob.file.path, action="copy")
        page_data = template_prob.page_data
    else:
        file = DbFile.from_file(problem)
        page_data = None

    prob = Problem(
        file=file,
        name=name,
        tournament=_tournament,
        start=start,
        end=end,
        image=_image,
        description=short_description,
        colour=colour.as_hex(),
        page_data=page_data
    )
    try:
        db.add(prob)
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", name) from e
    if page_data is None:
        background_tasks.add_task(prob.compute_page_data)
    return f"/problems/{prob.tournament.name}/{prob.name}"


@admin.patch("/problem", tags=["problem"], name="edit")
def edit_problem(
    *,
    db: Database,
    id: ID,
    name: str | None = None,
    tournament: ID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    description: str | None = None,
    alt_text: str | None = None,
    colour: Color | None = None,
    file: UploadFile | None = None,
    image: UploadFile | None | Literal["noedit"] = Form("noedit"),
    tasks: BackgroundTasks,
) -> Problem:
    problem = unwrap(db.get(Problem, id))
    if name:
        problem.name = name
    if tournament:
        problem.tournament = unwrap(db.get(Tournament, tournament))
    if start:
        problem.start = start
    if end:
        problem.end = end
    if description is not None:
        problem.description = description
    if alt_text is not None and problem.image is not None:
        problem.image.alt_text = alt_text
    if colour:
        problem.colour = colour.as_hex()
    if file:
        problem.file = DbFile.from_file(file)
        tasks.add_task(problem.compute_page_data)
    if image is None:
        problem.image = None
    elif image != "noedit":
        problem.image = DbFile.from_file(image)
    try:
        db.commit()
    except IntegrityError as e:
        raise ValueTaken("name", "") from e
    return problem


@admin.delete("/problem", tags=["problem"], name="delete")
def delete_problem(*, db: Database, id: ID) -> bool:
    problem = unwrap(db.get(Problem, id))
    db.delete(problem)
    db.commit()
    return True


# *******************************************************************************
# * Reports
# *******************************************************************************


@router.put("/report", tags=["report"])
def add_report(
    *,
    db: Database,
    team: TeamIfAdmin,
    problem: ID,
    file: UploadFile,
) -> Report:
    problem_model = Problem.get_unwrap(db, problem)
    if problem_model.tournament != team.tournament:
        raise HTTPException(400, "Selected team and problem are not in the same tournament")
    report = db.scalars(select(Report).where(Report.team == team, Report.problem == problem)).unique().first()
    if report:
        report.file = DbFile.from_file(file)
    else:
        report = Report(team, problem_model, DbFile.from_file(file))
        db.add(report)
    db.commit()
    return report


@router.delete("/report", tags=["report"])
def delete_report(db: Database, team: TeamIfAdmin, problem: ID) -> None:
    report = db.scalar(select(Report).where(Report.team == team, Report.problem_id == problem))
    if report is None:
        raise HTTPException(404, "No such report exists")
    db.delete(report)
    db.commit()


class Reports(BaseSchema):
    reports: dict[UUID, schemas.Report]
    total: int


@router.get("/report", tags=["report"])
def get_reports(
    db: Database, user: CurrUser, problem: UUID | None = None, team: UUID | None = None, offset: int = 0
) -> Reports:
    filters = [Report.visible_sql(user)]
    if problem:
        filters.append(Report.problem_id == problem)
    if team:
        filters.append(Report.team_id == team)

    reports = db.scalars(select(Report).where(*filters).limit(SQL_LIMIT).offset(offset)).all()
    count = db.scalar(select(func.count()).select_from(Report).where(*filters)) or 0
    return Reports(reports=encode(reports), total=count)


# *******************************************************************************
# * Program
# *******************************************************************************


class ProgramResults(BaseSchema):
    programs: dict[ID, schemas.Program]
    teams: dict[ID, schemas.Team]
    problems: dict[ID, schemas.Problem]
    page: int
    max_page: int


@router.get("/program/search", tags=["program"])
def search_program(
    *,
    db: Database,
    user: User = Depends(curr_user),
    name: str | None = None,
    team: ID | None = None,
    role: Role | None = None,
    problem: ID | None = None,
    limit: int = 25,
    page: int = 1,
) -> ProgramResults:
    if user.is_admin:
        problems = Problem.get_all(db)
    else:
        assert user.settings.selected_team is not None
        problems = (
            db.scalars(
                select(Problem).where(
                    Problem.visible_sql(user), Problem.tournament_id == user.settings.selected_team.tournament_id
                )
            )
            .unique()
            .all()
        )
    filters = [Program.visible_sql(user)]
    if name is not None:
        filters.append(Program.name.contains(name, autoescape=True))
    if team is not None:
        filters.append(Program.team_id == team)
    if role is not None:
        filters.append(Program.role == role)
    if problem is not None:
        filters.append(Program.problem_id == problem)
    page = max(page - 1, 0)
    programs = (
        db.scalars(
            select(Program).where(*filters).order_by(Program.creation_time.desc()).limit(limit).offset(page * limit)
        )
        .unique()
        .all()
    )
    total_count = db.scalar(select(func.count()).select_from(Program).where(*filters)) or 0
    teams = [program.team for program in programs]
    return ProgramResults(
        programs=encode(programs),
        teams=encode(teams),
        problems=encode(problems),
        page=page + 1,
        max_page=total_count // limit + 1,
    )


@router.post("/program/upload", tags=["program"])
def upload_program(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    name: str = "",
    role: Role,
    problem: ID,
    file: UploadFile = File(),
) -> Program:
    team = unwrap(user.settings.selected_team)
    problem_obj = unwrap(db.get(Problem, problem))
    problem_obj.assert_visible(user)
    prog = Program(name, team, role, DbFile.from_file(file), problem_obj)
    db.add(prog)
    db.commit()
    return prog


@router.post("/program/{id}/delete", tags=["program"])
def delete_program(*, db: Session = Depends(get_db), user: CurrUser, id: ID) -> bool:
    program = unwrap(db.get(Program, id))
    program.assert_editable(user)
    db.delete(program)
    db.commit()
    return True


# *******************************************************************************
# * Match
# *******************************************************************************


class ScheduleInfo(BaseSchema):
    matches: dict[ID, schemas.ScheduledMatch]
    problems: dict[ID, schemas.Problem]


@router.get("/match/schedule/get", tags=["match"])
def scheduled_matches(
    *,
    db: Session = Depends(get_db),
    user: User = Depends(curr_user),
    tournament: str | None = None,
) -> ScheduleInfo:
    if tournament is None:
        tournament_ = unwrap(user.settings.selected_team).tournament
    else:
        tournament_ = unwrap(db.get(Tournament, tournament))
    matches = (
        db.scalars(
            select(ScheduledMatch)
            .join(ScheduledMatch.problem)
            .where(Problem.tournament_id == tournament_.id, Problem.visible_sql(user))
        )
        .unique()
        .all()
    )
    return ScheduleInfo(matches=encode(matches), problems=encode(match.problem for match in matches))


@admin.post("/match/schedule/create", tags=["match"])
def create_schedule(
    *,
    db: Session = Depends(get_db),
    name: str = "",
    time: datetime,
    problem: ID,
    points: int,
) -> ScheduledMatch:
    problem_ = unwrap(db.get(Problem, problem))
    schedule = ScheduledMatch(time=time, problem=problem_, name=name, points=points)
    db.add(schedule)
    db.commit()
    return schedule


@admin.post("/match/schedule/{id}/edit", tags=["match"])
def edit_schedule(
    *,
    db: Session = Depends(get_db),
    id: ID,
    name: str | None = None,
    time: datetime | None = None,
    problem: ID | None = None,
    points: float | None = None,
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


@admin.post("/match/schedule/{id}/delete", tags=["match"])
def delete_schedule(*, db: Session = Depends(get_db), id: ID) -> bool:
    match = unwrap(db.get(ScheduledMatch, id))
    db.delete(match)
    db.commit()
    return True


class MatchResultData(BaseSchema):
    problems: dict[ID, schemas.Problem]
    results: dict[ID, schemas.MatchResult]
    teams: dict[ID, schemas.Team]


@router.get("/match/result", tags=["match"])
def results(*, db: Database, tournament: CurrTournament) -> MatchResultData:
    results = db.scalars(select(MatchResult).join(Problem).where(Problem.tournament_id == tournament.id)).unique().all()
    return MatchResultData(
        results=encode(results),
        problems=encode(result.problem for result in results),
        teams=encode(participant.team for result in results for participant in result.participants),
    )


@admin.delete("/match/result", tags=["match"])
def delete_results(*, db: Database, ids: list[ID]) -> None:
    for id in ids:
        db.delete(unwrap(db.get(MatchResult, id)))
    db.commit()


@admin.post("/match/result", tags=["match"], response_model=schemas.MatchResult)
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


@admin.put("/match/result", tags=["match"], response_model=schemas.MatchResult)
def update_result(
    db: Database,
    result: UUID,
    time: datetime,
    problem: UUID,
    status: MatchStatus,
    teams: InForm[list[UUID]],
    generators: InForm[list[UUID]],
    solvers: InForm[list[UUID]],
    points: InForm[list[float]],
    logs: UploadFile | UUID | None = None,
) -> MatchResult:
    res = MatchResult.get_unwrap(db, result)
    res.time = time
    res.problem = Problem.get_unwrap(db, problem)
    res.status = status
    if logs is None:
        res.logs = None
    elif isinstance(logs, UUID):
        res.logs = DbFile.get_unwrap(db, logs)
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
