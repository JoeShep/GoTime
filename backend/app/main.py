from fastapi import FastAPI

from app.models import Recommendation
from app.reasoning import recommend_next_step
from app.scenarios import build_relocation_scenario

app = FastAPI(title="GoTime API")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/recommendations/primary", response_model=Recommendation)
async def primary_recommendation() -> Recommendation:
    return recommend_next_step(build_relocation_scenario())
