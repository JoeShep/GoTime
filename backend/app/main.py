from fastapi import FastAPI, HTTPException, Request, status

from app.models import Recommendation, WorkArrangement
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
) -> Recommendation:
    unexpected_parameters = set(request.query_params) - {"work_arrangement"}
    if unexpected_parameters:
        names = ", ".join(sorted(unexpected_parameters))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported query parameter(s): {names}.",
        )

    goal = build_relocation_scenario()
    if work_arrangement is not None:
        goal = build_work_arrangement_scenario(goal, work_arrangement)

    try:
        return recommend_next_step(goal)
    except UnsupportedReasoningStateError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
