from fastapi import FastAPI, HTTPException, Query, Request, status

from app.models import (
    LIKELY_WORKPLACE_AREA_MAX_LENGTH,
    Recommendation,
    WorkArrangement,
)
from app.reasoning import UnsupportedReasoningStateError, recommend_next_step
from app.scenarios import (
    build_relocation_scenario,
    build_work_arrangement_scenario,
)

app = FastAPI(title="GoTime API")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recommendations/primary", response_model=Recommendation)
async def primary_recommendation(
    request: Request,
    work_arrangement: WorkArrangement | None = None,
    acceptable_commute_minutes: int | None = Query(default=None, gt=0),
    likely_workplace_area: str | None = Query(
        default=None, max_length=LIKELY_WORKPLACE_AREA_MAX_LENGTH
    ),
) -> Recommendation:
    unexpected_parameters = set(request.query_params) - {
        "work_arrangement",
        "acceptable_commute_minutes",
        "likely_workplace_area",
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

    goal = build_relocation_scenario()
    if work_arrangement is not None:
        goal = build_work_arrangement_scenario(
            goal,
            work_arrangement,
            acceptable_commute_minutes,
            likely_workplace_area,
        )

    try:
        return recommend_next_step(goal)
    except UnsupportedReasoningStateError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
