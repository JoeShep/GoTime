"""Offline fail-closed tests for the inactive v2 authorization package."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from v2_authorization_candidate import (  # noqa: E402
    CANDIDATE_MANIFEST_PATH,
    CANDIDATE_PATH,
    EXECUTION_MANIFEST_PATH,
    V2AuthorizationCandidateError,
    dry_run_activation_readiness,
    load_inactive_candidate_package,
    validate_activation_values,
    validate_candidate_artifact,
)
from v2_follow_up_authorization import (  # noqa: E402
    V2FollowUpAuthorizationError,
    load_manifest_bound_v2_authorization,
)


def artifact() -> dict[str, object]:
    return tomllib.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))


class ExplodingEnvironment(dict[str, str]):
    def __contains__(self, key: object) -> bool:
        raise AssertionError(f"environment inspected: {key}")
    def get(self, key: str, default=None):
        raise AssertionError(f"environment inspected: {key}")


def test_candidate_package_is_inactive_digest_bound_and_non_authoritative() -> None:
    verified = load_inactive_candidate_package()
    manifest = json.loads(CANDIDATE_MANIFEST_PATH.read_text())
    assert verified.digest == hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest()
    assert manifest["candidate_digest"] == verified.digest
    assert verified.artifact["metadata"]["active_repository_authority"] is False
    assert set(verified.artifact["authorization"].values()) == {False}
    assert "approver_identity" in verified.blockers


def test_candidate_cannot_satisfy_active_validator_or_replace_closed_state() -> None:
    before = EXECUTION_MANIFEST_PATH.read_bytes()
    with pytest.raises(V2FollowUpAuthorizationError, match="authorization is closed"):
        load_manifest_bound_v2_authorization(
            EXECUTION_MANIFEST_PATH, repository_root=REPOSITORY_ROOT
        )
    load_inactive_candidate_package()
    assert EXECUTION_MANIFEST_PATH.read_bytes() == before


def test_dry_run_never_inspects_environment_or_constructs_external_capability() -> None:
    result = dry_run_activation_readiness(ExplodingEnvironment())
    assert result["environment_inspected"] is False
    assert result["client_constructed"] is False
    assert result["network_request_made"] is False
    assert result["inactive"] is True


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("scope", "run_series_id", "wrong-series"),
        ("scope", "sequence", 2),
        ("scope", "fixture_id", "complete"),
        ("bindings", "prompt_version", "moving-service-questions-prompt-v1"),
        ("bindings", "schema_version", "moving-service-questions-schema-v1"),
        ("bindings", "frozen_v2_manifest_digest", "0" * 64),
        ("bindings", "provider_schema_digest", "0" * 64),
        ("bindings", "provider", "Other"),
        ("bindings", "ai_model_identifier", "other-model"),
        ("bindings", "sdk_pin", "openai==0"),
        ("scope", "maximum_token_preflight_requests", 2),
        ("scope", "maximum_ai_generation_requests", 2),
        ("scope", "automatic_retries", 1),
        ("scope", "maximum_total_spend_usd", "0.04"),
        ("proposed_authorization", "stage_c_authorized", True),
        ("proposed_authorization", "formal_evaluation_authorized", True),
        ("proposed_authorization", "production_use_authorized", True),
    ],
)
def test_candidate_rejects_scope_identity_digest_or_permission_drift(
    section: str, field: str, value: object
) -> None:
    changed = copy.deepcopy(artifact())
    changed[section][field] = value  # type: ignore[index]
    with pytest.raises(V2AuthorizationCandidateError):
        validate_candidate_artifact(changed)


def test_candidate_rejects_unknown_fields_and_non_single_use_shape() -> None:
    changed = copy.deepcopy(artifact())
    changed["scope"]["unknown"] = True  # type: ignore[index]
    with pytest.raises(V2AuthorizationCandidateError):
        validate_candidate_artifact(changed)
    changed = copy.deepcopy(artifact())
    changed["consumption"]["reuse_after_consumption"] = True  # type: ignore[index]
    with pytest.raises(V2AuthorizationCandidateError, match="Single-use"):
        validate_candidate_artifact(changed)


def test_missing_approver_and_timestamp_placeholders_block_activation() -> None:
    now = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    with pytest.raises(V2AuthorizationCandidateError, match="approver"):
        validate_activation_values(
            approver="APPROVER_ID_REQUIRED",
            approved_at="2030-01-01T12:00:00Z",
            activated_at="2030-01-01T12:00:00Z",
            expires_at="2030-01-01T12:15:00Z",
            now=now,
        )
    with pytest.raises(V2AuthorizationCandidateError, match="approver"):
        validate_activation_values(
            approver="",
            approved_at="2030-01-01T12:00:00Z",
            activated_at="2030-01-01T12:00:00Z",
            expires_at="2030-01-01T12:15:00Z",
            now=now,
        )
    with pytest.raises(V2AuthorizationCandidateError, match="placeholders"):
        validate_activation_values(
            approver="Human Reviewer",
            approved_at="APPROVED_AT_UTC_REQUIRED",
            activated_at="ACTIVATED_AT_UTC_REQUIRED",
            expires_at="EXPIRES_AT_UTC_REQUIRED",
            now=now,
        )


def test_expired_or_excessive_window_is_rejected() -> None:
    now = datetime(2030, 1, 1, 12, 20, tzinfo=timezone.utc)
    with pytest.raises(V2AuthorizationCandidateError, match="expired"):
        validate_activation_values(
            approver="Human Reviewer",
            approved_at="2030-01-01T12:00:00Z",
            activated_at="2030-01-01T12:00:00Z",
            expires_at="2030-01-01T12:15:00Z",
            now=now,
        )
    with pytest.raises(V2AuthorizationCandidateError, match="exceeds"):
        validate_activation_values(
            approver="Human Reviewer",
            approved_at="2030-01-01T12:00:00Z",
            activated_at="2030-01-01T12:00:00Z",
            expires_at="2030-01-01T12:15:01Z",
            now=datetime(2030, 1, 1, 12, 1, tzinfo=timezone.utc),
        )


def test_exact_900_second_future_values_are_structurally_valid() -> None:
    activated = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)
    validate_activation_values(
        approver="Human Reviewer",
        approved_at="2030-01-01T11:59:59Z",
        activated_at="2030-01-01T12:00:00Z",
        expires_at=(activated + timedelta(seconds=900)).isoformat().replace("+00:00", "Z"),
        now=activated + timedelta(seconds=1),
    )
