"""Future-live fixed sequence-4 generation entry point; zero token preflights."""

from __future__ import annotations

import json
import hashlib
import os
import tomllib
from datetime import datetime, timezone

from openai_client_factory import (
    CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES,
    construct_v2_preflight_openai_client_with_pinned_sdk,
)
from openai_transport import OpenAIPreflightResult
from openai_transport_v2 import make_v2_openai_transport
from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, prepare_frozen_v2_pilot
from v2_sequence_4_generation_gate import (
    CONSERVATIVE_COST, INPUT_TOKENS, OPERATOR_INTENT, PROVIDER_FINGERPRINT,
    REPOSITORY_ROOT, close_generation_authority,
    consume_preflight_evidence_for_generation, generation_paths, write_generation_outcome,
)


def main() -> int:
    now = datetime.now(timezone.utc)
    paths = generation_paths(DEFAULT_OUTPUT_ROOT)
    execution_path = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    manifest = json.loads(execution_path.read_text())
    active_digest = hashlib.sha256(paths.active.read_bytes()).hexdigest() if paths.active.exists() else None
    activation = json.loads(paths.activation.read_text()) if paths.activation.exists() else {}
    transaction = json.loads(paths.transaction.read_text()) if paths.transaction.exists() else {}
    if (manifest.get("status") != "active_v2_generation_only" or manifest.get("sequence") != 4
            or manifest.get("token_preflight_authorized") is not False
            or manifest.get("ai_generation_authorized") is not True
            or active_digest != manifest.get("authorization_digest")
            or activation.get("authorization_digest") != active_digest
            or activation.get("active_manifest_digest") != hashlib.sha256(execution_path.read_bytes()).hexdigest()
            or transaction.get("artifact_digest") != active_digest):
        raise ValueError("sequence-4 generation authority is not active")
    if transaction.get("state") != "committed" or paths.audit.exists():
        raise ValueError("sequence-4 generation transaction is not reusable")
    artifact = tomllib.loads(paths.active.read_text())
    expires = datetime.fromisoformat(artifact["approval"]["expires_at"].replace("Z", "+00:00"))
    if (expires - now).total_seconds() < 180:
        raise ValueError("insufficient generation authorization time remains")
    if os.environ.get("GOTIME_MOVING_SERVICE_EVAL_ENABLED") != "1" or os.environ.get("GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT") != OPERATOR_INTENT:
        raise ValueError("generation operator controls are invalid")
    credential = os.environ.get("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY")
    if not credential or any(name in os.environ for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
        raise ValueError("generation credential is unavailable")
    prepared = prepare_frozen_v2_pilot()
    client = None
    succeeded = False
    try:
        consume_preflight_evidence_for_generation(output_root=DEFAULT_OUTPUT_ROOT,
            authorization_digest=str(manifest["authorization_digest"]), now=now)
        client = construct_v2_preflight_openai_client_with_pinned_sdk(credential)
        transport = make_v2_openai_transport(client.client, prepared)
        if transport.request_fingerprint(prepared.provider_request) != PROVIDER_FINGERPRINT:
            raise ValueError("preflighted request fingerprint drifted")
        result = transport.generate(prepared.provider_request, OpenAIPreflightResult(
            PROVIDER_FINGERPRINT, INPUT_TOKENS, 0.0, CONSERVATIVE_COST))
        if result.error_classification is not None:
            raise ValueError("bounded generation provider failure")
        outcome = write_generation_outcome(output_root=DEFAULT_OUTPUT_ROOT, raw=result.response_content, now=now)
        for key in ("generation_succeeded", "validation_outcome", "response_evidence_sha256", "fallback_used"):
            print(f"{key}={outcome[key]}")
        succeeded = True
        return 0
    finally:
        if client is not None:
            client.close()
        close_generation_authority(repository_root=REPOSITORY_ROOT, output_root=DEFAULT_OUTPUT_ROOT,
                                   reason="success" if succeeded else "bounded_failure",
                                   now=datetime.now(timezone.utc))


if __name__ == "__main__":
    raise SystemExit(main())
