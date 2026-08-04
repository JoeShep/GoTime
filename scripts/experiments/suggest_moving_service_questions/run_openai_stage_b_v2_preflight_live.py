"""Future-live, single-use sequence-2 v2 token-preflight entry point."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from openai_client_factory import (
    construct_v2_preflight_openai_client_with_pinned_sdk,
)
from openai_transport_v2 import make_v2_openai_transport
from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from run_openai_stage_b_v2_two_gate import PREFLIGHT_INTENT, execute_v2_preflight_offline
from v2_preflight_authorization_activation import (
    load_active_preflight_authorization,
    recover_preflight_activation,
)

SEQUENCE = 2


def run(*, environment=None, now=None, active_loader=load_active_preflight_authorization,
        client_builder=construct_v2_preflight_openai_client_with_pinned_sdk,
        transport_factory=make_v2_openai_transport, output_root=DEFAULT_OUTPUT_ROOT,
        closure_operation=recover_preflight_activation):
    """Validate all non-secret authority before touching the supplied environment."""
    current = now or datetime.now(timezone.utc)
    active = active_loader(now=current, expected_sequence=SEQUENCE)
    source = os.environ if environment is None else environment

    def construct(credential: str):
        return client_builder(credential)

    def transport(owned, prepared):
        return transport_factory(owned.client, prepared)

    def close(reason: str) -> bool:
        record = closure_operation(
            reason=reason, now=datetime.now(timezone.utc),
            output_root=output_root, sequence=SEQUENCE,
        )
        return bool(record["authorization_closed"])

    return execute_v2_preflight_offline(
        authorization=active.authorization, environment=source,
        operator_intent=source.get("GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT", ""), output_root=output_root,
        client_constructor=construct, transport_factory=transport,
        closure=close, now=current, sequence=SEQUENCE,
        active_manifest_digest=active.manifest_digest,
        activation_record_digest=active.activation_digest,
    )


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
