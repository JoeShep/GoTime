"""Network-disabled fake-client sequence-3 preflight."""
from decimal import Decimal
from openai_transport import OpenAIPreflightResult
from run_openai_stage_b_v2_sequence_3_preflight_live import run

class Owned:
    def __init__(self): self.client = object(); self.closed = False
    def close(self): self.closed = True

class Transport:
    generation_calls = 0
    def request_fingerprint(self, request): return "3" * 64
    def preflight(self, request): return OpenAIPreflightResult("3" * 64, 2176, 1.0, Decimal("0.0016704"))
    def generate(self, *args, **kwargs): self.generation_calls += 1; raise AssertionError("generation unreachable")

def main():
    owned = Owned(); transport = Transport()
    result = run(client_builder=lambda credential: owned, transport_factory=lambda client, prepared: transport)
    if not result["preflight_succeeded"] or not owned.closed or transport.generation_calls: return 6
    print("preflight_succeeded=true"); print("generation_attempted=false"); print("authorization_closed=true")
    return 0

if __name__ == "__main__": raise SystemExit(main())
