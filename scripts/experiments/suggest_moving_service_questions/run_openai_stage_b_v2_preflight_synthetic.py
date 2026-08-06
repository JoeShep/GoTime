"""Network-free fake-client execution of the real sequence-2 preflight runner."""
from __future__ import annotations

from decimal import Decimal

from openai_transport import OpenAIPreflightResult
from run_openai_stage_b_v2_preflight_live import run


class _OwnedClient:
    def __init__(self) -> None:
        self.client = object()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _SyntheticTransport:
    generation_calls = 0

    def request_fingerprint(self, request) -> str:
        return "f" * 64

    def preflight(self, request) -> OpenAIPreflightResult:
        return OpenAIPreflightResult("f" * 64, 2176, 1.0, Decimal("0.0016704"))

    def generate(self, *args, **kwargs):
        self.generation_calls += 1
        raise AssertionError("generation is unreachable from sequence-2 preflight")


def main() -> int:
    owned = _OwnedClient()
    transport = _SyntheticTransport()
    result = run(client_builder=lambda credential: owned, transport_factory=lambda client, prepared: transport)
    if not result["preflight_succeeded"] or not owned.closed or transport.generation_calls:
        return 6
    print("preflight_succeeded=true")
    print("generation_attempted=false")
    print("authorization_closed=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
