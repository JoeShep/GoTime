"""Static and network-disabled boundaries for the fixed generation operator workflow."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts/experiments/suggest_moving_service_questions"

PUBLIC = (
    "render_v2_sequence_4_generation_authorization_candidate_docker.sh",
    "install_v2_sequence_4_generation_authorization_for_review_docker.sh",
    "review_v2_sequence_4_generation_authorization_activation_docker.sh",
    "plan_v2_sequence_4_generation_authorization_activation_docker.sh",
    "activate_v2_sequence_4_generation_authorization_docker.sh",
    "verify_v2_sequence_4_generation_authorization_docker.sh",
    "run_openai_stage_b_v2_sequence_4_generation_docker.sh",
    "run_v2_sequence_4_live_generation_operator.zsh",
    "review_v2_sequence_4_generation_response_docker.sh",
    "delete_v2_sequence_4_generation_response_evidence_docker.sh",
    "close_v2_sequence_4_generation_authorization_docker.sh",
)


def test_public_commands_exist_are_executable_and_fixed() -> None:
    for name in PUBLIC:
        path = SCRIPTS / name
        assert path.is_file() and path.stat().st_mode & 0o111
        text = path.read_text()
        assert "--sequence" not in text
        assert "--api-key" not in text


def test_same_shell_credential_boundary_and_traps() -> None:
    text = (SCRIPTS / "run_v2_sequence_4_live_generation_operator.zsh").read_text()
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in text
    assert "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_GENERATION_ONLY" in text
    assert "trap cleanup_generation_environment EXIT" in text
    assert "trap 'exit 130' INT" in text
    assert "trap 'exit 143' TERM" in text
    assert "trap 'exit 129' HUP" in text
    assert "local exit_code=$?" in text
    assert "local status=" not in text
    assert text.count("unset GOTIME_MOVING_SERVICE_EVAL_") == 3


def test_live_generation_has_no_preflight_call_and_credential_is_not_an_argument() -> None:
    runner = (SCRIPTS / "run_openai_stage_b_v2_sequence_4_generation_live.py").read_text()
    launcher = (SCRIPTS / "run_openai_stage_b_v2_sequence_4_generation_docker.sh").read_text()
    assert ".preflight(" not in runner
    assert "maximum_token_preflight_requests" not in launcher
    assert "--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" in launcher
    assert "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY}" not in launcher
    assert "--network none" not in launcher  # future live path; tests use the rehearsal wrapper


def test_rehearsal_is_network_disabled() -> None:
    wrapper = (SCRIPTS / "v2_sequence_4_generation_operator_docker.sh").read_text()
    assert "--network none" in wrapper


def test_every_runbook_script_exists_and_is_executable() -> None:
    runbook = (ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/sequence-4-generation-operator-runbook.md").read_text()
    referenced = set(re.findall(r"scripts/experiments/suggest_moving_service_questions/[A-Za-z0-9_.-]+", runbook))
    assert referenced
    for relative in referenced:
        path = ROOT / relative
        assert path.is_file(), relative
        assert path.stat().st_mode & 0o111, relative
