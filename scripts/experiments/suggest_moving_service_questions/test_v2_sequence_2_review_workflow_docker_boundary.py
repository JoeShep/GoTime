"""Offline static checks for the pinned sequence-2 review-workflow launchers."""

from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
OPERATIONS = {
    "install": "install_v2_sequence_2_preflight_authorization_for_review",
    "review": "review_v2_sequence_2_preflight_authorization_activation",
    "plan": "plan_v2_sequence_2_preflight_authorization_activation",
}


def _text(operation: str, suffix: str) -> str:
    return (SCRIPT_ROOT / f"{OPERATIONS[operation]}_{suffix}.sh").read_text(encoding="utf-8")


def test_all_launchers_use_pinned_network_disabled_environment_without_forwarding() -> None:
    for operation in OPERATIONS:
        text = _text(operation, "docker")
        assert "gotime-moving-service-stage-b:openai-2.45.0" in text
        assert "--network none" in text
        assert '--user "$(id -u):$(id -g)"' in text
        assert "--read-only" in text
        assert "pip install" not in text
        for prohibited in (
            "GOTIME_MOVING_SERVICE_EVAL", "OPENAI_API_KEY", "OPENAI_PROJECT_ID",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        ):
            assert prohibited not in text


def test_each_container_wrapper_invokes_only_its_fixed_cli() -> None:
    for operation, cli in OPERATIONS.items():
        text = _text(operation, "container")
        assert 'version("openai") == "2.45.0"' in text
        assert 'version("pydantic") == "2.13.4"' in text
        assert f"{cli}.py" in text
        for other in set(OPERATIONS.values()) - {cli}:
            assert f"{other}.py" not in text
        for prohibited in (
            "activate_v2_", "run_openai_stage_b_v2_preflight", "openai_client_factory",
            "openai_transport",
        ):
            assert prohibited not in text


def test_mounts_match_each_operation_write_boundary() -> None:
    install = _text("install", "docker")
    review = _text("review", "docker")
    plan = _text("plan", "docker")
    assert "--volume /tmp:/tmp:ro" in install
    assert "authorization-review:rw" in install
    assert "authorization-review:rw" in review
    assert "authorization-review:rw" not in plan
    assert "moving-service-stage-b-v2-pilot-20260802:ro" in plan


def test_public_launchers_expose_no_scope_override() -> None:
    text = "".join(_text(operation, "docker") for operation in OPERATIONS)
    for option in (
        "--sequence", "--provider", "--model", "--fixture", "--scope",
        "--permission", "--timeout", "--limit", "--spend", "--manifest",
    ):
        assert option not in text
