"""Static checks for the pinned sequence-2 renderer launcher."""

from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
DOCKER_LAUNCHER = SCRIPT_ROOT / "render_v2_sequence_2_preflight_authorization_candidate_docker.sh"
CONTAINER_WRAPPER = SCRIPT_ROOT / "render_v2_sequence_2_preflight_authorization_candidate_container.sh"


def test_launcher_uses_only_pinned_network_disabled_renderer_boundary() -> None:
    text = DOCKER_LAUNCHER.read_text(encoding="utf-8")
    assert "gotime-moving-service-stage-b:openai-2.45.0" in text
    assert "--network none" in text
    assert '--user "$(id -u):$(id -g)"' in text
    assert "--read-only" in text
    assert "--volume /tmp:/tmp:rw" in text
    assert "render_v2_sequence_2_preflight_authorization_candidate_container.sh" in text
    assert "GOTIME_MOVING_SERVICE_EVAL" not in text
    assert "OPENAI_API_KEY" not in text
    assert "pip install" not in text


def test_container_wrapper_checks_pins_then_invokes_exact_renderer() -> None:
    text = CONTAINER_WRAPPER.read_text(encoding="utf-8")
    assert 'version("openai") == "2.45.0"' in text
    assert 'version("pydantic") == "2.13.4"' in text
    assert (
        "exec python scripts/experiments/suggest_moving_service_questions/"
        "render_v2_sequence_2_preflight_authorization_candidate.py \"$@\""
    ) in text
    for prohibited in (
        "install_v2_", "review_v2_", "plan_v2_", "activate_v2_",
        "run_openai_stage_b_v2_preflight", "openai_client_factory", "openai_transport",
    ):
        assert prohibited not in text


def test_public_launcher_exposes_no_scope_override() -> None:
    text = DOCKER_LAUNCHER.read_text(encoding="utf-8") + CONTAINER_WRAPPER.read_text(encoding="utf-8")
    for option in (
        "--sequence", "--provider", "--model", "--fixture", "--permission",
        "--timeout", "--maximum-spend", "--manifest", "--digest",
    ):
        assert option not in text
