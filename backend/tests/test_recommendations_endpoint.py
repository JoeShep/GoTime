import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


async def get_primary_recommendation() -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        return await client.get("/api/recommendations/primary")


def test_primary_recommendation_endpoint() -> None:
    response = asyncio.run(get_primary_recommendation())

    assert response.status_code == 200
    assert response.json() == {
        "what": (
            "Clarify spouse employment requirements before choosing a final target location."
        ),
        "why": [
            "Employment requirements affect which locations are viable.",
            "Employment income affects housing affordability.",
            "The target-location decision is only partially ready.",
            "Several downstream decisions and actions depend on resolving this uncertainty.",
        ],
        "why_now": (
            "Employment requirements are the highest-leverage unresolved input that "
            "can be clarified now; defining them makes it possible to evaluate the "
            "separate assumption that suitable employment exists and avoids rework "
            "downstream."
        ),
        "related_decision_id": "target-location",
        "relevant_dependencies": [
            "Employment location or remote-work requirements",
            "Expected employment income",
            "Commute expectations",
            "Acceptable work arrangement",
        ],
        "blocked_downstream_work": [
            "Housing affordability analysis",
            "Commute viability analysis",
            "Healthcare access research",
            "Neighborhood research",
            "Move sequencing",
        ],
        "related_assumptions": [
            {
                "id": "spouse-employment",
                "description": (
                    "Suitable employment for the spouse exists within one or more "
                    "viable Northern California candidate regions."
                ),
                "status": "unconfirmed",
                "related_decision_ids": ["target-location"],
                "validation_method": (
                    "Evaluate regional employment opportunities through market research, "
                    "employer conversations, interviews, or job offers."
                ),
            }
        ],
    }
