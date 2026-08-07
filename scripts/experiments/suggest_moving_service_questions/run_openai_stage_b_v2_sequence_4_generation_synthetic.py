"""Network-disabled fake-client sequence-4 generation entry point."""

from __future__ import annotations

import os

from real_model_adapter import MovingServiceTransportResult
from run_openai_stage_b_v2_sequence_4_generation_live import run
from v2_sequence_4_generation_operator_cli import (
    synthetic_rejected_response,
    synthetic_valid_response,
)


class OwnedClient:
    def __init__(self) -> None:
        self.client = object()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeGenerationTransport:
    preflight_calls = 0

    def __init__(self, prepared, scenario: str) -> None:
        self.prepared = prepared
        self.scenario = scenario
        self.generation_calls = 0

    def request_fingerprint(self, request) -> str:
        from v2_sequence_4_generation_gate import PROVIDER_FINGERPRINT

        return PROVIDER_FINGERPRINT

    def preflight(self, request):
        self.preflight_calls += 1
        raise AssertionError("token preflight is unreachable")

    def generate(self, request, preflight) -> MovingServiceTransportResult:
        self.generation_calls += 1
        if self.scenario == "compliant":
            response = synthetic_valid_response()
        elif self.scenario == "prose_rejection":
            response = synthetic_rejected_response()
        elif self.scenario == "structural_failure":
            response = []
        else:
            response = synthetic_valid_response()
            response["suggestions"][0]["selected_missing_information_category"] = "packing_preference"
        return MovingServiceTransportResult(response_content=response)


def main() -> int:
    scenario = os.environ.get("GOTIME_V2_SEQUENCE_4_GENERATION_SYNTHETIC_SCENARIO", "compliant")
    owned = OwnedClient()
    transport_holder = {}

    def factory(client, prepared):
        transport = FakeGenerationTransport(prepared, scenario)
        transport_holder["transport"] = transport
        return transport

    outcome = run(client_builder=lambda credential: owned, transport_factory=factory)
    transport = transport_holder["transport"]
    if not owned.closed or transport.preflight_calls or transport.generation_calls != 1:
        return 6
    for key in (
        "generation_succeeded",
        "validation_outcome",
        "response_evidence_sha256",
        "fallback_used",
    ):
        print(f"{key}={outcome[key]}")
    print("synthetic_generation_calls=1")
    print("synthetic_preflight_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
