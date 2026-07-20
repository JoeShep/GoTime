import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.scenarios import build_relocation_scenario


async def get_primary_recommendation(query: str = "") -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        return await client.get(f"/api/recommendations/primary{query}")


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


def test_unclear_query_preserves_default_recommendation() -> None:
    default_response = asyncio.run(get_primary_recommendation())
    unclear_response = asyncio.run(
        get_primary_recommendation("?employment_requirements=unclear")
    )

    assert unclear_response.status_code == 200
    assert unclear_response.json() == default_response.json()


def test_clarified_requirements_recommendation_endpoint() -> None:
    response = asyncio.run(
        get_primary_recommendation("?employment_requirements=clarified")
    )

    assert response.status_code == 200
    assert response.json() == {
        "what": (
            "Evaluate candidate locations against the clarified employment requirements."
        ),
        "why": [
            "Clarified employment requirements provide criteria for comparing locations.",
            "Candidate evaluation can test where suitable employment may exist.",
            "The suitable-employment assumption remains unconfirmed.",
            "The target-location decision is still only partially ready.",
        ],
        "why_now": (
            "The requirements are now known, so candidate regions can be evaluated "
            "without prematurely choosing a final location."
        ),
        "related_decision_id": "target-location",
        "relevant_dependencies": [
            "Housing affordability",
            "Commute viability",
            "Healthcare access",
            "Suitable employment availability",
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


def test_unsupported_employment_requirements_value_returns_422() -> None:
    response = asyncio.run(
        get_primary_recommendation("?employment_requirements=unsupported")
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "employment_requirements"]
    assert "unclear" in response.json()["detail"][0]["msg"]
    assert "clarified" in response.json()["detail"][0]["msg"]


def test_recognized_state_without_reasoning_path_returns_explained_422(
    monkeypatch,
) -> None:
    goal_without_target_decision = build_relocation_scenario().model_copy(
        update={"decisions": ()}
    )
    monkeypatch.setattr(
        "app.main.build_relocation_scenario",
        lambda: goal_without_target_decision,
    )

    response = asyncio.run(
        get_primary_recommendation("?employment_requirements=unclear")
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The relocation reasoning rule does not apply to this goal."
    }
