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


@pytest.mark.parametrize(("value", "label"), (("hybrid", "Hybrid"), ("on_site", "On-site")))
def test_commuting_arrangement_without_limit_requests_boundary(
    value: str, label: str
) -> None:
    response = asyncio.run(get_primary_recommendation(f"?work_arrangement={value}"))

    assert response.status_code == 200
    recommendation = response.json()
    assert recommendation["what"] == (
        "Define the longest workable one-way commute before evaluating "
        "candidate locations."
    )
    assert label in recommendation["why"][0]
    assert recommendation["related_assumptions"][0]["status"] == "unconfirmed"


@pytest.mark.parametrize(
    "value",
    ("hybrid", "on_site"),
)
def test_valid_commute_limit_is_used_as_an_evaluation_boundary(
    value: str,
) -> None:
    response = asyncio.run(
        get_primary_recommendation(
            f"?work_arrangement={value}&acceptable_commute_minutes=45"
        )
    )

    assert response.status_code == 200
    recommendation = response.json()
    assert recommendation["what"] == (
        "Gather a likely workplace area before collecting commute evidence."
    )
    assert "longer than 45 minutes would not be acceptable" in recommendation["why"][0]
    assert "No route or travel time has been calculated." in recommendation["why"]
    assert "No candidate location currently passes or fails" in recommendation["why"][-2]
    assert recommendation["related_assumptions"][0]["status"] == "unconfirmed"


@pytest.mark.parametrize("value", ("hybrid", "on_site"))
def test_valid_likely_workplace_area_requests_travel_mode(
    value: str,
) -> None:
    response = asyncio.run(
        get_primary_recommendation(
            f"?work_arrangement={value}&acceptable_commute_minutes=45"
            "&likely_workplace_area=%20San%20Jose%20"
        )
    )

    assert response.status_code == 200
    recommendation = response.json()
    assert recommendation["what"] == (
        "Clarify the most likely commute travel mode before gathering "
        "travel-time evidence."
    )
    assert "user-provided likely workplace area" in recommendation["why"][0]
    assert "No route or travel time has been calculated." in recommendation["why"]
    assert "No candidate location currently passes or fails" in recommendation["why"][-2]
    assert recommendation["related_assumptions"][0]["status"] == "unconfirmed"


@pytest.mark.parametrize("work_arrangement", ("hybrid", "on_site"))
@pytest.mark.parametrize(
    ("travel_mode", "evidence_text", "mode_reason"),
    (
        (
            "drive",
            "one-way driving-time evidence",
            "traffic conditions remain unresolved",
        ),
        (
            "public_transit",
            "one-way public-transit travel-time evidence",
            "schedules, transfers, and station access remain unresolved",
        ),
        (
            "either",
            "one-way driving and public-transit evidence",
            "Both modes are acceptable",
        ),
    ),
)
def test_valid_travel_mode_produces_mode_specific_evidence_recommendation(
    work_arrangement: str,
    travel_mode: str,
    evidence_text: str,
    mode_reason: str,
) -> None:
    response = asyncio.run(
        get_primary_recommendation(
            f"?work_arrangement={work_arrangement}"
            "&acceptable_commute_minutes=45"
            "&likely_workplace_area=San%20Jose"
            f"&travel_mode={travel_mode}"
        )
    )

    assert response.status_code == 200
    recommendation = response.json()
    assert evidence_text in recommendation["what"]
    assert "likely San Jose workplace area" in recommendation["what"]
    assert "user-provided planning context" in recommendation["why"][2]
    assert "public_transit" not in " ".join(recommendation["why"])
    assert "No route or travel time has been calculated." in recommendation["why"]
    assert mode_reason in recommendation["why"][4]
    assert "No candidate location currently passes or fails" in recommendation["why"][-2]
    assert recommendation["related_assumptions"][0]["status"] == "unconfirmed"


def test_unsupported_work_arrangement_value_returns_422() -> None:
    response = asyncio.run(get_primary_recommendation("?work_arrangement=unknown"))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "work_arrangement"]
    assert "remote" in response.json()["detail"][0]["msg"]
    assert "flexible" in response.json()["detail"][0]["msg"]


@pytest.mark.parametrize(
    "query",
    (
        "?work_arrangement=hybrid&acceptable_commute_minutes=0",
        "?work_arrangement=hybrid&acceptable_commute_minutes=-1",
        "?work_arrangement=hybrid&acceptable_commute_minutes=45.5",
        "?work_arrangement=hybrid&acceptable_commute_minutes=invalid",
    ),
)
def test_invalid_commute_limit_returns_422(query: str) -> None:
    response = asyncio.run(get_primary_recommendation(query))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == [
        "query",
        "acceptable_commute_minutes",
    ]


@pytest.mark.parametrize(
    "query",
    (
        "?acceptable_commute_minutes=45",
        "?work_arrangement=remote&acceptable_commute_minutes=45",
        "?work_arrangement=flexible&acceptable_commute_minutes=45",
    ),
)
def test_incompatible_commute_limit_returns_422(query: str) -> None:
    response = asyncio.run(get_primary_recommendation(query))

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "acceptable_commute_minutes requires work_arrangement=hybrid "
            "or work_arrangement=on_site."
        )
    }


@pytest.mark.parametrize(
    "query",
    (
        "?likely_workplace_area=San%20Jose",
        "?work_arrangement=remote&acceptable_commute_minutes=45"
        "&likely_workplace_area=San%20Jose",
        "?work_arrangement=flexible&acceptable_commute_minutes=45"
        "&likely_workplace_area=San%20Jose",
        "?work_arrangement=hybrid&likely_workplace_area=San%20Jose",
    ),
)
def test_incompatible_likely_workplace_area_returns_422(query: str) -> None:
    response = asyncio.run(get_primary_recommendation(query))

    assert response.status_code == 422


@pytest.mark.parametrize(
    "value",
    ("", "%20%20%20"),
)
def test_blank_likely_workplace_area_returns_422(value: str) -> None:
    response = asyncio.run(
        get_primary_recommendation(
            "?work_arrangement=hybrid&acceptable_commute_minutes=45"
            f"&likely_workplace_area={value}"
        )
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "likely_workplace_area must not be blank."
    }


def test_over_length_likely_workplace_area_returns_422() -> None:
    response = asyncio.run(
        get_primary_recommendation(
            "?work_arrangement=hybrid&acceptable_commute_minutes=45"
            f"&likely_workplace_area={'a' * 121}"
        )
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "likely_workplace_area"]


def test_unsupported_travel_mode_returns_422() -> None:
    response = asyncio.run(
        get_primary_recommendation(
            "?work_arrangement=hybrid&acceptable_commute_minutes=45"
            "&likely_workplace_area=San%20Jose&travel_mode=walk"
        )
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "travel_mode"]
    assert "public_transit" in response.json()["detail"][0]["msg"]


@pytest.mark.parametrize(
    "query",
    (
        "?travel_mode=drive",
        "?work_arrangement=remote&acceptable_commute_minutes=45"
        "&likely_workplace_area=San%20Jose&travel_mode=drive",
        "?work_arrangement=flexible&acceptable_commute_minutes=45"
        "&likely_workplace_area=San%20Jose&travel_mode=drive",
        "?work_arrangement=hybrid&likely_workplace_area=San%20Jose"
        "&travel_mode=drive",
        "?work_arrangement=hybrid&acceptable_commute_minutes=45"
        "&travel_mode=drive",
    ),
)
def test_incompatible_travel_mode_returns_422(query: str) -> None:
    response = asyncio.run(get_primary_recommendation(query))

    assert response.status_code == 422


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
