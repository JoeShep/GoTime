from fastapi import FastAPI, HTTPException, status

from app.models import EmploymentRequirementsStatus, Recommendation
from app.reasoning import UnsupportedReasoningStateError, recommend_next_step
from app.scenarios import (
    build_clarified_employment_requirements_scenario,
    build_relocation_scenario,
)

app = FastAPI(title="GoTime API")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recommendations/primary", response_model=Recommendation)
async def primary_recommendation(
    employment_requirements: EmploymentRequirementsStatus = EmploymentRequirementsStatus.UNCLEAR,
) -> Recommendation:
    goal = build_relocation_scenario()
    if employment_requirements is EmploymentRequirementsStatus.CLARIFIED:
        goal = build_clarified_employment_requirements_scenario(goal)

    try:
        return recommend_next_step(goal)
    except UnsupportedReasoningStateError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
