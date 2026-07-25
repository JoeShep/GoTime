import asyncio

import pytest
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


@pytest.mark.parametrize(
    ("value", "expected_reason"),
    (
        ("remote", "routine workplace commute"),
        ("hybrid", "viable recurring commute"),
        ("on_site", "local employment availability"),
        ("flexible", "keeps more candidate regions viable"),
    ),
)
def test_work_arrangement_recommendation_endpoint(
    value: str, expected_reason: str
) -> None:
    response = asyncio.run(get_primary_recommendation(f"?work_arrangement={value}"))

    assert response.status_code == 200
    recommendation = response.json()
    assert recommendation["what"] == (
        "Evaluate candidate locations against the clarified employment requirements."
    )
    assert expected_reason in recommendation["why"][0]
    assert recommendation["why_now"].startswith(
        "The acceptable work arrangement is now known"
    )
    assert recommendation["related_assumptions"][0]["status"] == "unconfirmed"
    assert "The suitable-employment assumption remains unconfirmed." in recommendation["why"]


def test_unsupported_work_arrangement_value_returns_422() -> None:
    response = asyncio.run(get_primary_recommendation("?work_arrangement=unknown"))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "work_arrangement"]
    assert "remote" in response.json()["detail"][0]["msg"]
    assert "flexible" in response.json()["detail"][0]["msg"]


@pytest.mark.parametrize(
    ("query", "parameter"),
    (
        ("?employment_requirements=clarified", "employment_requirements"),
        ("?unexpected=value", "unexpected"),
    ),
)
def test_unexpected_query_parameter_returns_422(query: str, parameter: str) -> None:
    response = asyncio.run(get_primary_recommendation(query))

    assert response.status_code == 422
    assert response.json() == {
        "detail": f"Unsupported query parameter(s): {parameter}."
    }


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

    response = asyncio.run(get_primary_recommendation())

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The relocation reasoning rule does not apply to this goal."
    }
