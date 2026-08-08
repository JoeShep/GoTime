"""Frozen-v3 sequence-1 preflight identity and lifecycle tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import SkipTest

import pytest

SCRIPT = Path(__file__).resolve().parent
ROOT = SCRIPT.parents[2]
for value in (SCRIPT, ROOT / "backend"):
    if str(value) not in sys.path: sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v3_pilot import canonical_attempt_digest, deterministic_request_digest, prepare_frozen_v3_pilot  # noqa: E402
from v3_sequence_1_preflight import (  # noqa: E402
    CANDIDATE, CANDIDATE_DIGEST, CANONICAL_DIGEST, MANIFEST, MANIFEST_DIGEST,
    OPERATOR_INTENT, PROVIDER_FINGERPRINT, REQUEST_DIGEST, RUN_SERIES,
    RENDERED_TMP, V3PreflightError, activate, activation_review,
    generation_binding_dry_run, install, paths, render, review_evidence,
    verify_static,
)


def test_candidate_manifest_and_exact_v3_request_are_bound() -> None:
    status = verify_static()
    assert status == {"candidate_digest": CANDIDATE_DIGEST, "manifest_digest": MANIFEST_DIGEST, "request": REQUEST_DIGEST, "canonical": CANONICAL_DIGEST, "fingerprint": PROVIDER_FINGERPRINT}
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == CANDIDATE_DIGEST
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_DIGEST
    candidate = tomllib.loads(CANDIDATE.read_text())
    assert candidate["bindings"]["run_series_id"] == RUN_SERIES
    assert candidate["bindings"]["sequence"] == 1
    assert candidate["bindings"]["audit_prefix"] == "001-storage_unknown"
    assert candidate["authorization"] == {"credential_access_authorized": False, "token_preflight_authorized": False, "ai_generation_authorized": False}
    assert candidate["scope"]["maximum_token_preflight_requests"] == 1
    assert candidate["scope"]["maximum_ai_generation_requests"] == 0
    assert candidate["scope"]["automatic_retries"] == 0


def test_v3_request_differs_from_v2_and_mixed_identity_fails() -> None:
    v2 = prepare_frozen_v2_pilot(); v3 = prepare_frozen_v3_pilot()
    assert deterministic_request_digest(v3) == REQUEST_DIGEST
    assert canonical_attempt_digest(v3) == CANONICAL_DIGEST
    assert hashlib.sha256(v2.provider_request.deterministic_request_json.encode()).hexdigest() != REQUEST_DIGEST
    assert v2.provider_request.response_json_schema != v3.provider_request.response_json_schema
    with pytest.raises(Exception): type(v3.request).model_validate(v2.request.model_dump())
    with pytest.raises(Exception): type(v2.request).model_validate(v3.request.model_dump())


def test_every_operational_path_is_fixed_to_new_v3_series() -> None:
    target = paths(Path("/tmp/v3-state"), Path("/tmp/v3-repository"))
    operational = [value for key, value in vars(target).items() if key not in {"execution", "closed"}]
    for path in operational:
        assert "moving-service-stage-b-v3-pilot-20260807" in str(path)
        assert "001-storage_unknown" in path.name
        assert "004-storage_unknown" not in str(path)
        assert "moving-service-stage-b-v2-pilot-20260802" not in str(path)


def _closed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"; docs = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"; docs.mkdir(parents=True)
    closed = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    shutil.copyfile(closed, docs / "closed-execution-manifest.json"); shutil.copyfile(closed, docs / "execution-manifest.json")
    return repository


def _review_state(tmp_path: Path, *, late: bool = False) -> tuple[Path, Path, str]:
    output = tmp_path / "state"; repository = _closed_repository(tmp_path); target = paths(output, repository); target.evidence.parent.mkdir(parents=True)
    created = datetime(2030, 1, 1, tzinfo=timezone.utc); deadline = created + timedelta(seconds=30)
    evidence = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": "storage_unknown", "phase": "preflight", "frozen_v3_manifest_digest": "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c", "prompt_version": "moving-service-questions-prompt-v3", "schema_version": "moving-service-questions-schema-v3", "prompt_digest": "1146474ad5112a238446a63d4fc797022ca2cd65d8e9cb6c88935d7f4f3376e8", "provider_schema_digest": "333d6923902c46662243e019074b735500904bc49acbafdc1b929bceed9924e2", "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_preflight_fingerprint": PROVIDER_FINGERPRINT, "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5, "automatic_retries": 0, "generation_attempted": False, "input_tokens": 2300, "conservative_maximum_generation_cost": "0.0017200", "created_at": created.isoformat().replace("+00:00", "Z"), "review_deadline": deadline.isoformat().replace("+00:00", "Z")}
    target.evidence.write_text(json.dumps(evidence, sort_keys=True) + "\n")
    for record in (target.audit, target.consumption, target.closure): record.write_text("{}\n")
    return output, repository, hashlib.sha256(target.evidence.read_bytes()).hexdigest()


def test_immediate_review_and_generation_binding_are_non_authoritative(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    reviewed_at = "2030-01-01T00:00:10Z"; now = datetime(2030, 1, 1, 0, 0, 11, tzinfo=timezone.utc)
    result = review_evidence(evidence_sha256=evidence_digest, input_tokens=2300, conservative_cost="0.0017200", reviewer="Reviewer", decision="approve", reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Synthetic review", now=now, output_root=output, repository_root=repository)
    assert result["generation_gate_binding_eligible"] is True
    binding = generation_binding_dry_run(output_root=output)
    assert binding["writes_performed"] is False and binding["generation_authorized"] is False
    assert binding["preflight_evidence_digest"] == evidence_digest


def test_late_evidence_approval_fails_closed(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    with pytest.raises(V3PreflightError, match="invalid or late"):
        review_evidence(evidence_sha256=evidence_digest, input_tokens=2300, conservative_cost="0.0017200", reviewer="Reviewer", decision="approve", reviewed_at="2030-01-01T00:00:31Z", token_count_plausible=True, cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Late", now=datetime(2030, 1, 1, 0, 0, 31, tzinfo=timezone.utc), output_root=output, repository_root=repository)
    assert not paths(output, repository).evidence_review.exists()


def test_activation_interruption_recovers_permanent_closed_state(tmp_path) -> None:
    repository = _closed_repository(tmp_path); output = tmp_path / "state"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    RENDERED_TMP.unlink(missing_ok=True)
    try:
        rendered = render(approver="Synthetic", approved_at=(now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z"), activated_at=(now - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"), expires_at=(now + timedelta(seconds=895)).isoformat().replace("+00:00", "Z"), reason="Synthetic recovery", now=now)
        installed = install(source=RENDERED_TMP, expected_sha256=rendered["sha256"], now=now, output_root=output)
        reviewed = activation_review(artifact_sha256=rendered["sha256"], reviewer="Reviewer", decision="approve", reviewed_at=now.isoformat().replace("+00:00", "Z"), notes="Synthetic approval", now=now, output_root=output)
        with pytest.raises(OSError, match="synthetic interruption"):
            activate(artifact_sha256=rendered["sha256"], installation_sha256=installed["installation_record_digest"], review_sha256=reviewed["review_sha256"], operator="Operator", operator_intent=OPERATOR_INTENT, now=now, output_root=output, repository_root=repository, failpoint="manifest")
        target = paths(output, repository)
        assert target.execution.read_bytes() == target.closed.read_bytes()
        assert not target.active.exists()
        assert json.loads(target.transaction.read_text())["state"] == "rolled_back"
        assert json.loads(target.closure.read_text())["authorization_closed"] is True
    finally:
        RENDERED_TMP.unlink(missing_ok=True)


def test_runbook_inventory_is_fixed_and_executable() -> None:
    runbook = (ROOT / "docs/experiments/suggest-moving-service-questions/v3-preflight-operator-runbook.md").read_text()
    scripts = set(re.findall(r"scripts/experiments/suggest_moving_service_questions/[A-Za-z0-9_.-]+", runbook))
    assert "--sequence" not in runbook and "--version" not in runbook
    for relative in scripts:
        path = ROOT / relative
        assert path.is_file() and path.stat().st_mode & 0o111


def test_same_shell_script_preserves_credential_boundary_and_traps() -> None:
    text = (SCRIPT / "run_v3_live_preflight_operator.zsh").read_text()
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in text
    assert OPERATOR_INTENT in text
    assert "local exit_code=$?" in text and "local status=" not in text
    for signal, code in (("INT", 130), ("TERM", 143), ("HUP", 129)): assert f"trap 'exit {code}' {signal}" in text
    assert text.count("unset GOTIME_MOVING_SERVICE_EVAL_") == 3
    launcher = (SCRIPT / "run_openai_stage_b_v3_sequence_1_preflight_docker.sh").read_text()
    assert "--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" in launcher
    assert "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY}" not in launcher


def test_backend_frontend_have_no_v3_preflight_reachability() -> None:
    for root in (ROOT / "backend/app", ROOT / "frontend/src"):
        for path in root.rglob("*"):
            if path.is_file(): assert "moving-service-stage-b-v3-pilot-20260807" not in path.read_text(errors="ignore")


def _stubbed_operator(*, launcher_status: int = 0, signal_name: str | None = None,
                      closure_status: int = 0):
    if shutil.which("zsh") is None: raise SkipTest("zsh is required")
    with tempfile.TemporaryDirectory(prefix="gotime-v3-preflight-shell-") as directory:
        root = Path(directory); operator = SCRIPT / "run_v3_live_preflight_operator.zsh"
        copied = root / "scripts/experiments/suggest_moving_service_questions" / operator.name
        copied.parent.mkdir(parents=True); copied.write_bytes(operator.read_bytes()); copied.chmod(0o755)
        bin_path = root / "bin"; bin_path.mkdir(); log = root / "calls.log"
        action = f"kill -{signal_name} $PPID; exit 99" if signal_name else (
            'test "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" = synthetic-v3-secret || exit 88; '
            'test "$GOTIME_MOVING_SERVICE_EVAL_ENABLED" = 1 || exit 88; '
            f'test "$GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT" = {OPERATOR_INTENT} || exit 88; exit {launcher_status}'
        )
        stub = bin_path / "sh"
        stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$V3_CALL_LOG"\ncase "$*" in\n*verify*) exit 0;;\n*run_openai*) ' + action + f';;\n*close*) exit {closure_status};;\nesac\nexit 0\n'); stub.chmod(0o755)
        read_fd, write_fd = os.pipe(); os.write(write_fd, b"synthetic-v3-secret\n"); os.close(write_fd)
        environment = os.environ.copy(); environment.update({"PATH": f"{bin_path}:{environment['PATH']}", "GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST": "1", "GOTIME_V3_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD": str(read_fd), "V3_CALL_LOG": str(log)})
        result = subprocess.run(["zsh", str(copied)], cwd=root, env=environment, pass_fds=(read_fd,), text=True, capture_output=True, timeout=20); os.close(read_fd)
        return result, log.read_text()


def test_same_shell_success_failure_signals_and_closure_failure() -> None:
    success, calls = _stubbed_operator(); assert success.returncode == 0; assert "synthetic-v3-secret" not in success.stdout + success.stderr; assert "--reason success" in calls
    failure, calls = _stubbed_operator(launcher_status=9); assert failure.returncode == 9; assert "bounded_failure" in calls
    for signal, code in (("INT", 130), ("TERM", 143), ("HUP", 129)):
        result, calls = _stubbed_operator(signal_name=signal); assert result.returncode == code; assert "bounded_failure" in calls; assert "synthetic-v3-secret" not in result.stdout + result.stderr
    result, calls = _stubbed_operator(closure_status=17); assert result.returncode == 17; assert "--reason success" in calls and "bounded_failure" in calls
