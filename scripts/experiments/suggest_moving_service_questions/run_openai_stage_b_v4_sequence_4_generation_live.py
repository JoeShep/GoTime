"""Future-live fixed sequence-4 generation entry point; zero token preflights."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from openai_client_factory import (
    CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES,
    construct_v2_preflight_openai_client_with_pinned_sdk,
)
from openai_transport_v4 import make_v4_openai_transport
from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v4_sequence_4_generation_gate import (
    OPERATOR_INTENT, REPOSITORY_ROOT, close_generation_authority,
    consume_preflight_evidence_for_generation,
    verify_live_generation_precredential, write_generation_outcome,
)


def verify_attempt_then_read_credential(
    *, environment, now: datetime,
    attempt_verifier=verify_live_generation_precredential,
):
    """Cross the credential boundary only after exact request verification."""
    verified_attempt = attempt_verifier(
        output_root=DEFAULT_OUTPUT_ROOT, repository_root=REPOSITORY_ROOT, now=now)
    if environment.get("GOTIME_MOVING_SERVICE_EVAL_ENABLED") != "1" or environment.get("GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT") != OPERATOR_INTENT:
        raise ValueError("generation operator controls are invalid")
    credential = environment.get("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY")
    if not credential or any(name in environment for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
        raise ValueError("generation credential is unavailable")
    return verified_attempt, credential


def run(*, environment=os.environ, client_builder=construct_v2_preflight_openai_client_with_pinned_sdk,
        transport_factory=make_v4_openai_transport) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    verified_attempt, credential = verify_attempt_then_read_credential(
        environment=environment, now=now)
    client = None
    succeeded = False
    try:
        consume_preflight_evidence_for_generation(output_root=DEFAULT_OUTPUT_ROOT,
            authorization_digest=str(verified_attempt.authorization_digest), now=now)
        client = client_builder(credential)
        transport = transport_factory(client.client, verified_attempt.prepared)
        if transport.request_fingerprint(verified_attempt.prepared.provider_request) != verified_attempt.provider_fingerprint:
            raise ValueError("preflighted request fingerprint drifted")
        result = transport.generate(
            verified_attempt.prepared.provider_request, verified_attempt.preflight
        )
        if result.error_classification is not None:
            raise ValueError("bounded generation provider failure")
        outcome = write_generation_outcome(output_root=DEFAULT_OUTPUT_ROOT, raw=result.response_content, now=now)
        succeeded = True
        return dict(outcome)
    finally:
        if client is not None:
            client.close()
        close_generation_authority(repository_root=REPOSITORY_ROOT, output_root=DEFAULT_OUTPUT_ROOT,
                                   reason="success" if succeeded else "bounded_failure",
                                   now=datetime.now(timezone.utc))


def main() -> int:
    outcome = run()
    for key in ("generation_succeeded", "validation_outcome", "response_evidence_sha256", "fallback_used"):
        print(f"{key}={outcome[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
