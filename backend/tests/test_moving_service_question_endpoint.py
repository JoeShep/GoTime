import asyncio

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app.main import app


async def get_experiment(query: str) -> Response:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        return await client.get(
            f"/api/experiments/moving-service-question{query}"
        )


@pytest.mark.parametrize(
    ("scenario", "source", "fallback_reason"),
    (
        ("storage_unknown", "fake_ai_adapter", None),
        ("complete", "none", None),
        (
            "invalid_ai_response",
            "deterministic_fallback",
            "invalid_adapter_response",
        ),
        (
            "adapter_unavailable",
            "deterministic_fallback",
            "adapter_unavailable",
        ),
        ("adapter_timeout", "deterministic_fallback", "adapter_timeout"),
        (
            "budget_unavailable",
            "deterministic_fallback",
            "experimental_budget_unavailable",
        ),
        (
            "ai_disabled",
            "deterministic_fallback",
            "ai_assistance_disabled",
        ),
    ),
)
def test_temporary_fixture_endpoint_exposes_supported_paths(
    scenario: str, source: str, fallback_reason: str | None
) -> None:
    response = asyncio.run(get_experiment(f"?scenario={scenario}"))

    assert response.status_code == 200
    result = response.json()
    assert result["source"] == source
    assert result["observability"]["fixture_id"] == scenario
    assert result["observability"]["fallback_reason"] == fallback_reason
    assert result["observability"]["estimated_cost"] == "$0.00"


def test_endpoint_requires_a_fixture_scenario() -> None:
    response = asyncio.run(get_experiment(""))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "scenario"]


def test_unsupported_fixture_returns_422() -> None:
    response = asyncio.run(get_experiment("?scenario=not_supported"))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "scenario"]


def test_unexpected_query_parameter_returns_422() -> None:
    response = asyncio.run(
        get_experiment("?scenario=storage_unknown&unexpected=value")
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Unsupported query parameter(s): unexpected."
    }


def test_endpoint_exposes_no_mutation_or_trusted_state_contract() -> None:
    response = asyncio.run(get_experiment("?scenario=storage_unknown"))

    assert response.status_code == 200
    body = response.json()
    assert "trusted_state" not in body
    assert "state_update" not in body
    assert "proposed_state_field" not in str(body)
