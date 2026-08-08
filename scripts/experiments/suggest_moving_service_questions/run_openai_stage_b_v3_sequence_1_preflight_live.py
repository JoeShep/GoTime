"""Single-use frozen-v3 sequence-1 token-preflight entry point."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from openai_client_factory import construct_v2_preflight_openai_client_with_pinned_sdk
from v3_sequence_1_preflight import execute_preflight


def run(*, environment=None, now=None, client_builder=construct_v2_preflight_openai_client_with_pinned_sdk,
        transport_factory=None):
    options = {"environment": os.environ if environment is None else environment,
               "now": now or datetime.now(timezone.utc), "client_builder": client_builder}
    if transport_factory is not None: options["transport_factory"] = transport_factory
    return execute_preflight(**options)


def main() -> int:
    result = run()
    for key in ("preflight_succeeded", "input_tokens", "conservative_maximum_generation_cost", "duration_ms", "audit_digest", "evidence_digest"):
        print(f"{key}={result.get(key)}")
    print("generation_attempted=false")
    return 0 if result["preflight_succeeded"] else 6


if __name__ == "__main__": raise SystemExit(main())
