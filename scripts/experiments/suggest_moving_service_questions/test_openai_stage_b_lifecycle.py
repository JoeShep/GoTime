from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from manage_openai_stage_b_lifecycle import _parser
import openai_client_factory
from openai_client_factory import (
    EVALUATION_CREDENTIAL_NAME,
    OPENAI_API_BASE_URL,
    REQUIRED_NON_SECRET_GATE_ORDER,
    EvaluationCredentialError,
    build_stage_b_moving_service_openai_client_from_environment,
)
from run_openai_stage_b_pilot import (
    ENABLEMENT_ENVIRONMENT_NAME,
    OPERATOR_INTENT,
    SEQUENCE,
    StageBPilotError,
    _execute_stage_b,
    _require_exact_enablement,
    main as stage_b_main,
    run_stage_b_generation_pilot,
)
from run_real_model_evaluation import OfflineRunnerGateError
from stage_b_lifecycle import (
    CLOSED_ARTIFACT_PATH,
    CLOSED_AUTHORIZATION_DIGEST,
    FALLBACK_COMPARISONS,
    StageBLifecycleError,
    close_stage_b_authorization,
    delete_stage_b_response_evidence,
    finalize_stage_b_human_review,
    lifecycle_paths,
)
from stage_b_authorization import CONSUMED_THROUGH_SEQUENCE
from test_openai_stage_b_pilot import Owned, _package, _provider_response

REPO = Path(__file__).resolve().parents[3]


def _successful_attempt(tmp_path: Path, now: datetime):
    authorization, manifest = _package(tmp_path / "repo", now)
    output_root = tmp_path / "out"
    record = _execute_stage_b(
        authorization=authorization,
        manifest_path=manifest,
        environment={"synthetic": "only"},
        output_root=output_root,
        client_builder=lambda *args, **kwargs: Owned(_provider_response()),
        now=lambda: now,
    )
    return record, authorization, manifest, output_root


def _review(**overrides):
    value = {
        "human_review_status": "approved",
        "grounding_supported": True,
        "invented_user_fact_present": False,
        "scope_overstatement_present": False,
        "provider_or_service_recommendation_present": False,
        "storage_required_claim_present": False,
        "clarity_score": 4,
        "usefulness_score": 4,
        "fallback_comparison": "slightly_better",
        "reviewer": "reviewer-1",
        "bounded_review_notes": "Grounded within the supplied conditional statement.",
    }
    value.update(overrides)
    return value


def test_exact_live_entry_point_rejects_closed_authorization(monkeypatch):
    monkeypatch.setenv(ENABLEMENT_ENVIRONMENT_NAME, "1")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_openai_stage_b_pilot.py",
            "--run-series",
            "moving-service-stage-b-pilot-20260801",
            "--sequence",
            str(SEQUENCE),
            "--fixture",
            "storage_unknown",
            "--operator-intent",
            OPERATOR_INTENT,
        ],
    )
    with pytest.raises(OfflineRunnerGateError):
        stage_b_main()


def test_exact_live_entry_point_rejects_wrong_operator_literal(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_openai_stage_b_pilot.py",
            "--run-series",
            "moving-service-stage-b-pilot-20260801",
            "--sequence",
            str(SEQUENCE),
            "--fixture",
            "storage_unknown",
            "--operator-intent",
            "wrong",
        ],
    )
    with pytest.raises(SystemExit):
        stage_b_main()


@pytest.mark.parametrize("value", [None, "", "true", "yes", "0", " 1"])
def test_operator_enablement_accepts_only_exact_one(value):
    environment = {} if value is None else {ENABLEMENT_ENVIRONMENT_NAME: value}
    with pytest.raises(OfflineRunnerGateError):
        _require_exact_enablement(environment)
    _require_exact_enablement({ENABLEMENT_ENVIRONMENT_NAME: "1"})


def test_operator_intent_cannot_override_closed_authorization():
    class ExplodingEnvironment(dict):
        def get(self, *args):
            raise AssertionError("closed authorization must stop before environment access")

    with pytest.raises(OfflineRunnerGateError):
        run_stage_b_generation_pilot(
            environment=ExplodingEnvironment(), operator_intent=OPERATOR_INTENT
        )


def test_sequences_one_through_three_are_consumed_and_four_is_next():
    assert CONSUMED_THROUGH_SEQUENCE == 3
    assert SEQUENCE == 4


@pytest.mark.parametrize("credential", [None, ""])
def test_exact_docker_launcher_rejects_missing_or_empty_host_credential(
    tmp_path, credential
):
    audit_path = lifecycle_paths()["audit"]
    audit_before = audit_path.read_bytes() if audit_path.exists() else None
    docker_started = tmp_path / "docker-started"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        f'#!/bin/sh\ntouch "{docker_started}"\n', encoding="utf-8"
    )
    fake_docker.chmod(0o700)
    environment = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    environment.pop(EVALUATION_CREDENTIAL_NAME, None)
    if credential is not None:
        environment[EVALUATION_CREDENTIAL_NAME] = credential

    completed = subprocess.run(
        [
            "sh",
            str(
                REPO
                / "scripts/experiments/suggest_moving_service_questions/"
                "run_openai_stage_b_pilot_docker.sh"
            ),
        ],
        cwd=REPO,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 3
    assert not docker_started.exists()
    assert (audit_path.read_bytes() if audit_path.exists() else None) == audit_before
    assert "credential" in completed.stderr.lower()


@pytest.mark.parametrize("credential", [None, ""])
def test_container_wrapper_rejects_before_python_runner(tmp_path, credential):
    audit_path = lifecycle_paths()["audit"]
    audit_before = audit_path.read_bytes() if audit_path.exists() else None
    runner_started = tmp_path / "runner-started"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python"
    fake_python.write_text(
        f'#!/bin/sh\ntouch "{runner_started}"\n', encoding="utf-8"
    )
    fake_python.chmod(0o700)
    environment = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}
    environment.pop(EVALUATION_CREDENTIAL_NAME, None)
    if credential is not None:
        environment[EVALUATION_CREDENTIAL_NAME] = credential

    completed = subprocess.run(
        [
            "sh",
            str(
                REPO
                / "scripts/experiments/suggest_moving_service_questions/"
                "run_openai_stage_b_pilot_container.sh"
            ),
        ],
        cwd=REPO,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 3
    assert not runner_started.exists()
    assert (audit_path.read_bytes() if audit_path.exists() else None) == audit_before
    assert "credential" in completed.stderr.lower()


def test_exact_docker_launch_forwards_only_named_evaluation_variables(tmp_path):
    capture = tmp_path / "docker-arguments.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$GOTIME_DOCKER_ARGUMENT_CAPTURE"\n',
        encoding="utf-8",
    )
    fake_docker.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "GOTIME_DOCKER_ARGUMENT_CAPTURE": str(capture),
        "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic-secret-not-for-recording",
    }
    script = (
        REPO
        / "scripts/experiments/suggest_moving_service_questions/"
        "run_openai_stage_b_pilot_docker.sh"
    )
    completed = subprocess.run(
        ["sh", str(script)],
        cwd=REPO,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    arguments = capture.read_text(encoding="utf-8").splitlines()
    assert "GOTIME_MOVING_SERVICE_EVAL_ENABLED=1" in arguments
    assert "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" in arguments
    assert "synthetic-secret-not-for-recording" not in arguments
    assert arguments.count("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY") == 1
    assert "--user" in arguments
    assert "--read-only" in arguments
    assert arguments[-2:] == [
        "sh",
        "scripts/experiments/suggest_moving_service_questions/"
        "run_openai_stage_b_pilot_container.sh",
    ]


def test_forwarded_synthetic_credential_reaches_injected_stage_b_constructor(
    tmp_path, monkeypatch
):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    monkeypatch.setattr(openai_client_factory, "REPOSITORY_ROOT", tmp_path / "repo")
    synthetic_credential = "synthetic-docker-forwarding-proof"
    client_calls = []
    http_calls = []

    class FakeHttpClient:
        def close(self):
            pass

    class FakeOpenAIClient:
        max_retries = 0

        def close(self):
            pass

    def construct_http_client(**kwargs):
        http_calls.append(kwargs)
        return FakeHttpClient()

    def construct_client(**kwargs):
        client_calls.append(kwargs)
        return FakeOpenAIClient()

    owned = build_stage_b_moving_service_openai_client_from_environment(
        {EVALUATION_CREDENTIAL_NAME: synthetic_credential},
        completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
        operator_intent_confirmed=True,
        manifest_path=manifest,
        authorization_path=authorization.path,
        expected_authorization_digest=authorization.digest,
        sdk_version="2.45.0",
        client_constructor=construct_client,
        http_client_constructor=construct_http_client,
    )
    try:
        assert http_calls == [{"trust_env": False}]
        assert len(client_calls) == 1
        assert client_calls[0]["api_key"] == synthetic_credential
        assert client_calls[0]["base_url"] == OPENAI_API_BASE_URL
        assert client_calls[0]["max_retries"] == 0
    finally:
        owned.close()


def test_exact_launcher_reaches_injected_constructor_with_synthetic_credential(
    tmp_path
):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    marker = tmp_path / "constructor-reached"
    capture = tmp_path / "docker-arguments.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    probe = tmp_path / "constructor_probe.py"
    probe.write_text(
        """import os, sys
from pathlib import Path
sys.path.insert(0, os.environ["GOTIME_SCRIPT_ROOT"])
import openai_client_factory as factory
factory.REPOSITORY_ROOT = Path(os.environ["GOTIME_FAKE_REPOSITORY_ROOT"])
calls = []
class Http:
    def __init__(self, **kwargs): calls.append(("http", kwargs))
    def close(self): pass
class Client:
    def __init__(self, **kwargs):
        self.max_retries = kwargs["max_retries"]
        calls.append(("client", kwargs))
    def close(self): pass
owned = factory.build_stage_b_moving_service_openai_client_from_environment(
    {factory.EVALUATION_CREDENTIAL_NAME: os.environ[factory.EVALUATION_CREDENTIAL_NAME]},
    completed_non_secret_gates=factory.REQUIRED_NON_SECRET_GATE_ORDER,
    operator_intent_confirmed=True,
    manifest_path=Path(os.environ["GOTIME_FAKE_MANIFEST"]),
    authorization_path=Path(os.environ["GOTIME_FAKE_AUTHORIZATION"]),
    expected_authorization_digest=os.environ["GOTIME_FAKE_AUTHORIZATION_DIGEST"],
    sdk_version="2.45.0",
    client_constructor=Client,
    http_client_constructor=Http,
)
assert calls[0] == ("http", {"trust_env": False})
assert calls[1][1]["api_key"] == "synthetic-exact-launcher-proof"
assert calls[1][1]["max_retries"] == 0
owned.close()
Path(os.environ["GOTIME_CONSTRUCTOR_MARKER"]).write_text("reached", encoding="utf-8")
""",
        encoding="utf-8",
    )
    fake_python = fake_bin / "python"
    fake_python.write_text(
        '#!/bin/sh\nexec "$GOTIME_REAL_PYTHON" "$GOTIME_CONSTRUCTOR_PROBE"\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o700)
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$GOTIME_DOCKER_ARGUMENT_CAPTURE"\n'
        'exec sh "$GOTIME_CONTAINER_WRAPPER"\n',
        encoding="utf-8",
    )
    fake_docker.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        EVALUATION_CREDENTIAL_NAME: "synthetic-exact-launcher-proof",
        "GOTIME_DOCKER_ARGUMENT_CAPTURE": str(capture),
        "GOTIME_CONTAINER_WRAPPER": str(
            REPO
            / "scripts/experiments/suggest_moving_service_questions/"
            "run_openai_stage_b_pilot_container.sh"
        ),
        "GOTIME_REAL_PYTHON": sys.executable,
        "GOTIME_CONSTRUCTOR_PROBE": str(probe),
        "GOTIME_CONSTRUCTOR_MARKER": str(marker),
        "GOTIME_SCRIPT_ROOT": str(
            REPO / "scripts/experiments/suggest_moving_service_questions"
        ),
        "GOTIME_FAKE_REPOSITORY_ROOT": str(tmp_path / "repo"),
        "GOTIME_FAKE_MANIFEST": str(manifest),
        "GOTIME_FAKE_AUTHORIZATION": str(authorization.path),
        "GOTIME_FAKE_AUTHORIZATION_DIGEST": authorization.digest,
    }

    completed = subprocess.run(
        [
            "sh",
            str(
                REPO
                / "scripts/experiments/suggest_moving_service_questions/"
                "run_openai_stage_b_pilot_docker.sh"
            ),
        ],
        cwd=REPO,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert marker.read_text(encoding="utf-8") == "reached"
    assert "synthetic-exact-launcher-proof" not in capture.read_text(
        encoding="utf-8"
    )


def test_cli_rejects_wrong_fixed_values():
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["close", "--reason", "other"])


def test_credential_failure_audit_is_bounded(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)

    def fail(*args, **kwargs):
        raise EvaluationCredentialError("synthetic failure")

    with pytest.raises(StageBPilotError) as caught:
        _execute_stage_b(
            authorization=authorization,
            manifest_path=manifest,
            environment={},
            output_root=tmp_path / "out",
            client_builder=fail,
            now=lambda: now,
        )
    audit = json.loads(caught.value.record_path.read_text())
    assert audit["failure_stage"] == "credential_lookup"
    assert audit["credential_lookup_attempted"] is True
    assert audit["credential_value_obtained"] is False
    assert audit["client_construction_attempted"] is True
    assert audit["preflight_attempted"] is False
    assert audit["generation_attempted"] is False
    assert audit["authorization_closed"] is False
    assert "synthetic failure" not in caught.value.record_path.read_text()


def test_unexpected_failure_writes_complete_tombstone(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)

    def explode(*args, **kwargs):
        raise RuntimeError("must not be recorded")

    with pytest.raises(StageBPilotError) as caught:
        _execute_stage_b(
            authorization=authorization,
            manifest_path=manifest,
            environment={},
            output_root=tmp_path / "out",
            client_builder=explode,
            now=lambda: now,
        )
    audit = json.loads(caught.value.record_path.read_text())
    assert audit["failure_stage"] == "unexpected"
    assert audit["bounded_failure_classification"] == "unexpected_post_reservation_failure"
    for field in (
        "credential_lookup_attempted",
        "client_construction_attempted",
        "preflight_attempted",
        "generation_attempted",
        "authorization_closed",
    ):
        assert isinstance(audit[field], bool)
    assert "must not be recorded" not in caught.value.record_path.read_text()


@pytest.mark.parametrize(
    "change",
    [
        {"human_review_status": "pending"},
        {"clarity_score": 0},
        {"usefulness_score": 6},
        {"fallback_comparison": "better"},
        {"reviewer": ""},
        {"bounded_review_notes": "x" * 501},
        {"unknown": True},
        {"grounding_supported": False},
    ],
)
def test_human_review_rejects_unbounded_or_unknown_values(tmp_path, change):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _successful_attempt(tmp_path, now)
    review = _review()
    review.update(change)
    with pytest.raises(StageBLifecycleError):
        finalize_stage_b_human_review(
            review=review, output_root=tmp_path / "out", now=now
        )


def test_review_finalization_preserves_digest_then_deletes_evidence(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    original, _, _, output_root = _successful_attempt(tmp_path, now)
    paths = lifecycle_paths(output_root)
    original_evidence = paths["evidence"].read_bytes()
    result = finalize_stage_b_human_review(
        review=_review(), output_root=output_root, now=now + timedelta(minutes=1)
    )
    assert result["human_review_status"] == "approved"
    assert result["response_evidence_sha256"] == original.response_evidence_sha256
    assert not paths["evidence"].exists()
    assert paths["review"].exists() and paths["deletion"].exists()
    deletion_text = paths["deletion"].read_text()
    assert original_evidence.decode() not in deletion_text
    audit = json.loads(paths["audit"].read_text())
    assert audit["response_evidence_deleted"] is True
    assert audit["human_review_status"] == "approved"
    with pytest.raises(FileExistsError):
        finalize_stage_b_human_review(review=_review(), output_root=output_root, now=now)
    assert delete_stage_b_response_evidence(
        output_root=output_root,
        reason="review_signoff",
        review_status="approved",
        now=now,
    ) == json.loads(paths["deletion"].read_text())


def test_retention_deadline_is_enforced_and_missing_evidence_is_explicit(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _, _, _, output_root = _successful_attempt(tmp_path, now)
    with pytest.raises(StageBLifecycleError):
        delete_stage_b_response_evidence(
            output_root=output_root,
            reason="retention_deadline",
            review_status="not_reviewed",
            now=now + timedelta(days=29),
        )
    paths = lifecycle_paths(output_root)
    paths["evidence"].unlink()
    result = delete_stage_b_response_evidence(
        output_root=output_root,
        reason="retention_deadline",
        review_status="not_reviewed",
        now=now + timedelta(days=30),
    )
    assert result["evidence_existed_before_deletion"] is False
    assert result["deletion_completed"] is True


@pytest.mark.parametrize(
    "reason", ["success", "bounded_failure", "expiration", "operator_cancellation"]
)
def test_closure_restores_closed_authorization_and_is_idempotent(tmp_path, reason):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    closed_source = REPO / CLOSED_ARTIFACT_PATH
    closed_target = tmp_path / "repo" / CLOSED_ARTIFACT_PATH
    closed_target.parent.mkdir(parents=True, exist_ok=True)
    closed_target.write_bytes(closed_source.read_bytes())
    output_root = tmp_path / "out"
    first = close_stage_b_authorization(
        reason=reason,
        repository_root=tmp_path / "repo",
        manifest_path=manifest,
        output_root=output_root,
        now=now,
    )
    second = close_stage_b_authorization(
        reason=reason,
        repository_root=tmp_path / "repo",
        manifest_path=manifest,
        output_root=output_root,
        now=now,
    )
    assert first == second
    updated = json.loads(manifest.read_text())
    assert updated["openai_execution_authorization_path"] == CLOSED_ARTIFACT_PATH
    assert updated["openai_execution_authorization_digest"] == CLOSED_AUTHORIZATION_DIGEST
    assert not authorization.path.exists()
    assert first["closure_reason"] == reason
    assert first["ai_generation_permitted_after_closure"] is False


def test_closure_updates_existing_attempt_audit(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _, authorization, manifest, output_root = _successful_attempt(tmp_path, now)
    closed_source = REPO / CLOSED_ARTIFACT_PATH
    closed_target = tmp_path / "repo" / CLOSED_ARTIFACT_PATH
    closed_target.parent.mkdir(parents=True, exist_ok=True)
    closed_target.write_bytes(closed_source.read_bytes())
    close_stage_b_authorization(
        reason="success",
        repository_root=tmp_path / "repo",
        manifest_path=manifest,
        output_root=output_root,
        now=now,
    )
    audit = json.loads(lifecycle_paths(output_root)["audit"].read_text())
    assert audit["authorization_closed"] is True
    assert audit["closure_status"] == "closed_and_verified"
    assert Path(audit["closure_record_path"]).name.endswith("closure.json")
    assert not authorization.path.exists()


def test_lifecycle_modules_have_no_direct_network_operations():
    for name in (
        "run_openai_stage_b_pilot.py",
        "stage_b_lifecycle.py",
        "manage_openai_stage_b_lifecycle.py",
    ):
        text = (Path(__file__).parent / name).read_text()
        for prohibited in ("requests.", "urllib.", "socket.", "http://", "https://"):
            assert prohibited not in text
    assert FALLBACK_COMPARISONS == {
        "materially_better",
        "slightly_better",
        "equivalent",
        "slightly_worse",
        "materially_worse",
    }
