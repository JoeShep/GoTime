import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.models import (
    LIKELY_WORKPLACE_AREA_MAX_LENGTH,
    CommuteTravelMode,
    Recommendation,
    WorkArrangement,
)
from app.moving_service_questions import (
    ExperimentFixture,
    MovingServiceQuestionExperimentResult,
    run_experiment,
)
from app.reasoning import UnsupportedReasoningStateError, recommend_next_step
from app.relocation_plan_models import (
    DecisionCreate,
    DecisionSelectionUpdate,
    DecisionUpdate,
    MilestoneAchievementUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    RelocationPlan,
    TaskCreate,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.relocation_plan_repository import (
    DecisionNotFoundError,
    DependencyCycleError,
    DuplicateTitleError,
    InvalidDependencyError,
    InvalidHierarchyError,
    InvalidPhaseError,
    InvalidDecisionError,
    MilestoneNotFoundError,
    PlanItemAlreadyExistsError,
    ParentChangeConfirmationRequired,
    SQLiteRelocationPlanRepository,
    TaskAlreadyExistsError,
    TaskNotFoundError,
)
from app.relocation_plan_recommendation import (
    RelocationTaskRecommendation,
    recommend_relocation_task,
)
from app.scenarios import (
    build_relocation_scenario,
    build_work_arrangement_scenario,
)

DEFAULT_DATABASE_PATH = Path(os.environ.get("GOTIME_DATABASE_PATH", "data/gotime.db"))
router = APIRouter()


def experiments_enabled() -> bool:
    """Experiments are available only through an explicit, exact opt-in."""
    return os.environ.get("GOTIME_ENABLE_EXPERIMENTS") == "true"


def require_experiments_enabled() -> None:
    if not experiments_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def create_app(database_path: str | Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    application = FastAPI(title="GoTime API")
    application.state.database_path = Path(database_path)

    @application.middleware("http")
    async def gate_experiment_routes(request: Request, call_next):
        if request.url.path in {
            "/api/recommendations/primary",
            "/api/experiments/moving-service-question",
        } and not experiments_enabled():
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "Not Found"},
            )
        return await call_next(request)

    application.include_router(router)
    return application


def get_plan_repository(request: Request) -> SQLiteRelocationPlanRepository:
    repository = getattr(request.app.state, "plan_repository", None)
    if repository is None:
        repository = SQLiteRelocationPlanRepository(request.app.state.database_path)
        request.app.state.plan_repository = repository
    return repository


def plan_error(error: ValueError) -> HTTPException:
    if isinstance(error, (TaskNotFoundError, MilestoneNotFoundError, DecisionNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, DuplicateTitleError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, ParentChangeConfirmationRequired):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": error.code, "message": str(error)},
        )
    if isinstance(error, (TaskAlreadyExistsError, PlanItemAlreadyExistsError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, (InvalidPhaseError, InvalidDependencyError, InvalidHierarchyError, DependencyCycleError, InvalidDecisionError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/relocation-plan", response_model=RelocationPlan)
async def relocation_plan(request: Request) -> RelocationPlan:
    return get_plan_repository(request).get_plan()


@router.get(
    "/api/relocation-plan/recommendation",
    response_model=RelocationTaskRecommendation,
)
async def relocation_plan_recommendation(
    request: Request,
) -> RelocationTaskRecommendation:
    return recommend_relocation_task(get_plan_repository(request).get_plan())


@router.post(
    "/api/relocation-plan/tasks",
    response_model=RelocationPlan,
    status_code=status.HTTP_201_CREATED,
)
async def create_relocation_task(request: Request, task: TaskCreate) -> RelocationPlan:
    try:
        return get_plan_repository(request).create_task(task)
    except ValueError as error:
        raise plan_error(error) from error


@router.put("/api/relocation-plan/tasks/{task_id}", response_model=RelocationPlan)
async def update_relocation_task(
    request: Request, task_id: str, task: TaskUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).update_task(task_id, task)
    except ValueError as error:
        raise plan_error(error) from error


@router.patch(
    "/api/relocation-plan/tasks/{task_id}/status", response_model=RelocationPlan
)
async def update_relocation_task_status(
    request: Request, task_id: str, update: TaskStatusUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).update_task_status(
            task_id, update.status,
            confirm_manual_override=update.confirm_manual_override,
        )
    except ValueError as error:
        raise plan_error(error) from error


@router.delete(
    "/api/relocation-plan/tasks/{task_id}/status-override",
    response_model=RelocationPlan,
)
async def return_parent_to_automatic_status(
    request: Request, task_id: str,
) -> RelocationPlan:
    try:
        return get_plan_repository(request).return_parent_to_automatic_status(task_id)
    except ValueError as error:
        raise plan_error(error) from error


@router.post(
    "/api/relocation-plan/milestones",
    response_model=RelocationPlan,
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone(request: Request, milestone: MilestoneCreate) -> RelocationPlan:
    try:
        return get_plan_repository(request).create_milestone(milestone)
    except ValueError as error:
        raise plan_error(error) from error


@router.put(
    "/api/relocation-plan/milestones/{milestone_id}", response_model=RelocationPlan
)
async def update_milestone(
    request: Request, milestone_id: str, milestone: MilestoneUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).update_milestone(milestone_id, milestone)
    except ValueError as error:
        raise plan_error(error) from error


@router.patch(
    "/api/relocation-plan/milestones/{milestone_id}/achievement",
    response_model=RelocationPlan,
)
async def set_milestone_achievement(
    request: Request, milestone_id: str, update: MilestoneAchievementUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).set_milestone_achievement(
            milestone_id, update.achieved
        )
    except ValueError as error:
        raise plan_error(error) from error


@router.post(
    "/api/relocation-plan/decisions",
    response_model=RelocationPlan,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(request: Request, decision: DecisionCreate) -> RelocationPlan:
    try:
        return get_plan_repository(request).create_decision(decision)
    except ValueError as error:
        raise plan_error(error) from error


@router.put(
    "/api/relocation-plan/decisions/{decision_id}", response_model=RelocationPlan
)
async def update_decision(
    request: Request, decision_id: str, decision: DecisionUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).update_decision(decision_id, decision)
    except ValueError as error:
        raise plan_error(error) from error


@router.patch(
    "/api/relocation-plan/decisions/{decision_id}/selection",
    response_model=RelocationPlan,
)
async def select_decision_option(
    request: Request, decision_id: str, update: DecisionSelectionUpdate
) -> RelocationPlan:
    try:
        return get_plan_repository(request).select_decision_option(
            decision_id, update.selected_option_id
        )
    except ValueError as error:
        raise plan_error(error) from error


@router.get(
    "/api/experiments/moving-service-question",
    response_model=MovingServiceQuestionExperimentResult,
)
async def moving_service_question_experiment(
    request: Request,
    scenario: ExperimentFixture,
) -> MovingServiceQuestionExperimentResult:
    """Temporary fixture-only endpoint for the fake-adapter experiment."""
    require_experiments_enabled()
    unexpected_parameters = set(request.query_params) - {"scenario"}
    if unexpected_parameters:
        names = ", ".join(sorted(unexpected_parameters))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported query parameter(s): {names}.",
        )
    return run_experiment(scenario)


@router.get("/api/recommendations/primary", response_model=Recommendation)
async def primary_recommendation(
    request: Request,
    work_arrangement: WorkArrangement | None = None,
    acceptable_commute_minutes: int | None = Query(default=None, gt=0),
    likely_workplace_area: str | None = Query(
        default=None, max_length=LIKELY_WORKPLACE_AREA_MAX_LENGTH
    ),
    travel_mode: CommuteTravelMode | None = None,
) -> Recommendation:
    require_experiments_enabled()
    unexpected_parameters = set(request.query_params) - {
        "work_arrangement",
        "acceptable_commute_minutes",
        "likely_workplace_area",
        "travel_mode",
    }
    if unexpected_parameters:
        names = ", ".join(sorted(unexpected_parameters))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported query parameter(s): {names}.",
        )

    if acceptable_commute_minutes is not None and work_arrangement not in (
        WorkArrangement.HYBRID,
        WorkArrangement.ON_SITE,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "acceptable_commute_minutes requires work_arrangement=hybrid "
                "or work_arrangement=on_site."
            ),
        )

    if likely_workplace_area is not None:
        likely_workplace_area = likely_workplace_area.strip()
        if not likely_workplace_area:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="likely_workplace_area must not be blank.",
            )
        if (
            work_arrangement
            not in (WorkArrangement.HYBRID, WorkArrangement.ON_SITE)
            or acceptable_commute_minutes is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "likely_workplace_area requires work_arrangement=hybrid or "
                    "work_arrangement=on_site and acceptable_commute_minutes."
                ),
            )

    if travel_mode is not None and (
        work_arrangement not in (WorkArrangement.HYBRID, WorkArrangement.ON_SITE)
        or acceptable_commute_minutes is None
        or likely_workplace_area is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "travel_mode requires work_arrangement=hybrid or "
                "work_arrangement=on_site, acceptable_commute_minutes, and "
                "likely_workplace_area."
            ),
        )

    goal = build_relocation_scenario()
    if work_arrangement is not None:
        goal = build_work_arrangement_scenario(
            goal,
            work_arrangement,
            acceptable_commute_minutes,
            likely_workplace_area,
            travel_mode,
        )

    try:
        return recommend_next_step(goal)
    except UnsupportedReasoningStateError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error


app = create_app()
