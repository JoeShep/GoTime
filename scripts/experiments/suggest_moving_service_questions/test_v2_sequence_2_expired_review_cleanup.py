"""Offline tests for typed cleanup of an expired sequence-2 review package."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
for value in (SCRIPT_ROOT, REPOSITORY_ROOT / "backend"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from v2_phase_authorization_candidates import render_preflight_candidate_for_sequence  # noqa: E402
from v2_sequence_2_authorization_candidate import load_sequence_2_preflight_candidate  # noqa: E402
from v2_sequence_2_expired_review_cleanup import (  # noqa: E402
    CleanupError,
    cleanup_expired_sequence_2_review_package,
    verify_expired_sequence_2_review_package,
)
from v2_sequence_2_preflight_authorization import (  # noqa: E402
    install_sequence_2_for_review,
    review_sequence_2_activation,
)

ACTIVE = datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc)
EXPIRED = datetime(2030, 1, 1, 12, 20, tzinfo=timezone.utc)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    target = root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    target.mkdir(parents=True)
    source = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    for name in ("execution-manifest.json", "closed-execution-manifest.json", "openai-execution-authorization.toml"):
        (target / name).write_bytes((source / name).read_bytes())
    return root


def _package(tmp_path: Path):
    source = tmp_path / "gotime-v2-sequence-2-preflight-authorization.toml"
    rendered = render_preflight_candidate_for_sequence(
        sequence=2, candidate_loader=load_sequence_2_preflight_candidate,
        output_path=source, approver="Synthetic Approver",
        approved_at="2030-01-01T12:00:00Z", activated_at="2030-01-01T12:04:00Z",
        expires_at="2030-01-01T12:15:00Z", authorization_reason="Synthetic expired cleanup",
        now=ACTIVE,
    )
    output_root = tmp_path / "local"
    installation = install_sequence_2_for_review(
        source=source, expected_sha256=rendered.digest, now=ACTIVE, output_root=output_root,
    )
    review = review_sequence_2_activation(
        artifact_sha256=rendered.digest, reviewer="Synthetic Reviewer", decision="approve",
        reviewed_at="2030-01-01T12:06:00Z", notes="Synthetic cleanup review.",
        now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc), output_root=output_root,
    )
    return source, output_root, installation, review, _repository(tmp_path)


def _verify(package, *, now=EXPIRED):
    source, output_root, installation, review, repository = package
    return verify_expired_sequence_2_review_package(
        artifact_sha256=_digest(source),
        installation_record_sha256=installation["installation_record_sha256"],
        activation_review_sha256=review["review_sha256"], now=now,
        repository_root=repository, output_root=output_root, source_path=source,
    )


def _replace_artifact(package, old: str, new: str):
    source, output_root, installation, review, repository = package
    installed = output_root / "moving-service-stage-b-v2-pilot-20260802/authorization-review/002-storage_unknown-preflight-rendered.toml"
    value = source.read_text().replace(old, new, 1)
    assert value != source.read_text()
    source.write_text(value)
    installed.write_text(value)
    return source, output_root, installation, review, repository


def test_exact_expired_artifact_passes_authoritative_typed_validation(tmp_path: Path) -> None:
    verified = _verify(_package(tmp_path))
    assert verified.expires_at == "2030-01-01T12:15:00Z"
    assert len(verified.paths) == 4


def test_verifier_calls_established_typed_authorization_parser(monkeypatch, tmp_path: Path) -> None:
    import v2_sequence_2_expired_review_cleanup as module
    original = module.validate_phase_authorization
    calls = []

    def observed(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(module, "validate_phase_authorization", observed)
    _verify(_package(tmp_path))
    assert calls and calls[0]["phase"] == "preflight"
    assert calls[0]["expected_sequence"] == 2


@pytest.mark.parametrize("old,new", [
    ('phase = "preflight"', 'phase = "generation"'),
    ('ai_generation_authorized = false', 'ai_generation_authorized = true'),
    ('sequence = 2', 'sequence = 1'),
    ('run_series_id = "moving-service-stage-b-v2-pilot-20260802"', 'run_series_id = "wrong-series"'),
    ('frozen_v2_manifest_digest = "', 'frozen_v2_manifest_digest = "0'),
])
def test_wrong_phase_generation_sequence_run_or_frozen_binding_fails(tmp_path: Path, old: str, new: str) -> None:
    package = _replace_artifact(_package(tmp_path), old, new)
    with pytest.raises(CleanupError, match="typed preflight validation"):
        _verify(package)


def test_unexpired_artifact_is_not_cleanup_eligible(tmp_path: Path) -> None:
    with pytest.raises(CleanupError, match="not expired"):
        _verify(_package(tmp_path), now=ACTIVE)


def test_activated_review_fails(tmp_path: Path) -> None:
    package = _package(tmp_path)
    source, output_root, installation, review, repository = package
    review_path = output_root / "moving-service-stage-b-v2-pilot-20260802/authorization-review/002-storage_unknown-preflight-activation-review.json"
    value = json.loads(review_path.read_text())
    value["activated"] = True
    review_path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    review["review_sha256"] = _digest(review_path)
    with pytest.raises(CleanupError, match="indicates activation"):
        _verify(package)


def test_wrong_candidate_binding_fails(tmp_path: Path) -> None:
    package = _package(tmp_path)
    source, output_root, installation, review, repository = package
    review_dir = output_root / "moving-service-stage-b-v2-pilot-20260802/authorization-review"
    installation_path = review_dir / "002-storage_unknown-preflight-installation.json"
    installation_value = json.loads(installation_path.read_text())
    installation_value["candidate_digest"] = "0" * 64
    installation_path.write_text(json.dumps(installation_value, sort_keys=True, separators=(",", ":")) + "\n")
    installation["installation_record_sha256"] = _digest(installation_path)
    review_path = review_dir / "002-storage_unknown-preflight-activation-review.json"
    review_value = json.loads(review_path.read_text())
    review_value["installation_record_digest"] = installation["installation_record_sha256"]
    review_path.write_text(json.dumps(review_value, sort_keys=True, separators=(",", ":")) + "\n")
    review["review_sha256"] = _digest(review_path)
    with pytest.raises(CleanupError, match="lifecycle validation"):
        _verify(package)


@pytest.mark.parametrize("name", [
    "002-storage_unknown-preflight-activation.json",
    "002-storage_unknown-preflight-activation-transaction.json",
])
def test_existing_activation_or_transaction_fails(tmp_path: Path, name: str) -> None:
    package = _package(tmp_path)
    base = package[1] / "moving-service-stage-b-v2-pilot-20260802"
    (base / name).write_text("{}\n")
    with pytest.raises(CleanupError, match="used"):
        _verify(package)


def test_dry_run_identifies_exact_files_and_performs_no_deletion(tmp_path: Path) -> None:
    verified = _verify(_package(tmp_path))
    assert [path.name for path in verified.paths] == [
        "gotime-v2-sequence-2-preflight-authorization.toml",
        "002-storage_unknown-preflight-rendered.toml",
        "002-storage_unknown-preflight-installation.json",
        "002-storage_unknown-preflight-activation-review.json",
    ]
    assert all(path.exists() for path in verified.paths)
    assert not verified.cleanup_record.exists()


def test_confirmed_synthetic_cleanup_deletes_only_four_and_keeps_sequence_unused_closed(tmp_path: Path) -> None:
    package = _package(tmp_path)
    source, output_root, installation, review, repository = package
    base = output_root / "moving-service-stage-b-v2-pilot-20260802"
    sentinel = base / "unrelated-local-record.json"
    sentinel.write_text("{}\n")
    sentinel_digest = _digest(sentinel)
    result = cleanup_expired_sequence_2_review_package(
        artifact_sha256=_digest(source),
        installation_record_sha256=installation["installation_record_sha256"],
        activation_review_sha256=review["review_sha256"], now=EXPIRED,
        operator="Synthetic Operator", repository_root=repository,
        output_root=output_root, source_path=source,
    )
    assert result["deleted"] is True and result["sequence_2_unused"] is True
    record_path = Path(result["cleanup_record"])
    record = json.loads(record_path.read_text())
    assert record_path.stat().st_mode & 0o777 == 0o600
    assert set(record) == {
        "capability", "run_series_id", "sequence", "fixture_id", "reason", "paths",
        "pre_deletion_digests", "expired_at", "cleanup_timestamp",
        "execution_manifest_closed", "active_authorization_absent",
        "activation_record_absent", "transaction_journal_absent", "authoritative",
        "activated", "operator", "status", "deleted", "deletion_results",
        "credential_or_provider_operation_occurred", "sequence_consumed",
    }
    assert record["sequence_consumed"] is False
    assert sentinel.exists() and _digest(sentinel) == sentinel_digest
    pilot = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    assert (pilot / "execution-manifest.json").read_bytes() == (pilot / "closed-execution-manifest.json").read_bytes()
