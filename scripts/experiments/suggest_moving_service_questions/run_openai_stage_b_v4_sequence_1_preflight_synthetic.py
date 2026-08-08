"""Network-disabled fake frozen-v4 sequence-1 preflight."""

from decimal import Decimal

from openai_transport import OpenAIPreflightResult
from run_openai_stage_b_v4_sequence_1_preflight_live import run
from v4_sequence_1_preflight import PROVIDER_FINGERPRINT


class Owned:
    def __init__(self): self.client = object(); self.closed = False
    def close(self): self.closed = True


class Transport:
    generation_calls = 0
    def request_fingerprint(self, request): return PROVIDER_FINGERPRINT
    def preflight(self, request):
        if request is not self.prepared.provider_request:
            raise AssertionError("preflight did not receive the verified prepared request")
        return OpenAIPreflightResult(PROVIDER_FINGERPRINT, 4242, 1.0, Decimal("0.0024242"))
    def generate(self, *args, **kwargs): self.generation_calls += 1; raise AssertionError("generation unreachable")


def main() -> int:
    owned = Owned(); transport = Transport()
    def factory(client, prepared):
        transport.prepared = prepared
        return transport
    result = run(client_builder=lambda credential: owned, transport_factory=factory)
    if not result["preflight_succeeded"] or not owned.closed or transport.generation_calls: return 6
    print("preflight_succeeded=true"); print("input_tokens=4242"); print("conservative_maximum_generation_cost=0.0024242"); print("generation_attempted=false"); print("authorization_closed=true")
    return 0


if __name__ == "__main__": raise SystemExit(main())
