"""Network-free tests for the future-live sequence-2 preflight path."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parents[2] / "backend"
for value in (ROOT, BACKEND):
    if str(value) not in sys.path: sys.path.insert(0, str(value))

from openai_transport import OpenAIPreflightResult, TransportErrorClassification  # noqa: E402
from run_openai_stage_b_v2_preflight_live import run  # noqa: E402
from run_openai_stage_b_v2_two_gate import PREFLIGHT_INTENT  # noqa: E402
from v2_two_gate_authorization import VerifiedV2PhaseAuthorization  # noqa: E402

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


class Owned:
    def __init__(self): self.client = object(); self.closed = False
    def close(self): self.closed = True


class Transport:
    def __init__(self, result): self.result = result; self.calls = 0; self.generation_calls = 0
    def request_fingerprint(self, request): return "f" * 64
    def preflight(self, request): self.calls += 1; return self.result
    def generate(self, *args): self.generation_calls += 1; raise AssertionError("generation unreachable")


def active():
    authorization = VerifiedV2PhaseAuthorization("preflight", "a" * 64, NOW, NOW + timedelta(minutes=10))
    return SimpleNamespace(authorization=authorization, manifest_digest="m" * 64, activation_digest="r" * 64)


def test_sequence_two_success_is_single_use_bounded_and_closes(tmp_path: Path):
    owned = Owned(); transport = Transport(OpenAIPreflightResult("f" * 64, 2176, 12.5, Decimal("0.0016704")))
    closures = []
    state = run(
        environment={"GOTIME_MOVING_SERVICE_EVAL_ENABLED": "1", "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT": PREFLIGHT_INTENT, "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic"},
        now=NOW, active_loader=lambda **kw: active(), client_builder=lambda value: owned,
        transport_factory=lambda client, prepared: transport, output_root=tmp_path,
        closure_operation=lambda **kw: closures.append(kw) or {"authorization_closed": True},
    )
    base = tmp_path / "moving-service-stage-b-v2-pilot-20260802"
    audit = json.loads((base / "002-storage_unknown-preflight.json").read_text())
    assert state["preflight_succeeded"] and audit["sequence"] == 2
    assert audit["generation_attempted"] is False and transport.calls == 1 and transport.generation_calls == 0
    assert owned.closed and closures[0]["sequence"] == 2 and closures[0]["reason"] == "success"
    assert (base / "002-storage_unknown-preflight-evidence.json").stat().st_mode & 0o777 == 0o600
    assert not (base / "002-storage_unknown-preflight-evidence-consumption.json").exists()
    with pytest.raises(FileExistsError):
        run(environment={"GOTIME_MOVING_SERVICE_EVAL_ENABLED":"1","GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT":PREFLIGHT_INTENT,"GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY":"x"}, now=NOW,
            active_loader=lambda **kw: active(), client_builder=lambda value: Owned(),
            transport_factory=lambda client, prepared: transport, output_root=tmp_path,
            closure_operation=lambda **kw: {"authorization_closed": True})


@pytest.mark.parametrize("environment", [{}, {"GOTIME_MOVING_SERVICE_EVAL_ENABLED":"0"}, {"GOTIME_MOVING_SERVICE_EVAL_ENABLED":"1","GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT":PREFLIGHT_INTENT,"OPENAI_API_KEY":"x","GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY":"y"}])
def test_environment_failures_consume_close_and_never_construct(tmp_path: Path, environment):
    constructed=[]; closures=[]
    with pytest.raises(Exception):
        run(environment=environment, now=NOW, active_loader=lambda **kw: active(),
            client_builder=lambda value: constructed.append(value), output_root=tmp_path,
            closure_operation=lambda **kw: closures.append(kw) or {"authorization_closed": True})
    assert not constructed and closures and closures[0]["reason"] == "bounded_failure"


def test_closed_authority_rejects_before_environment_access():
    class Exploding(dict):
        def get(self, key, default=None): raise AssertionError("environment inspected")
    with pytest.raises(RuntimeError):
        run(environment=Exploding(), now=NOW, active_loader=lambda **kw: (_ for _ in ()).throw(RuntimeError("closed")))


def test_timeout_is_bounded_closes_and_never_retries(tmp_path: Path):
    owned=Owned(); transport=Transport(OpenAIPreflightResult("f"*64, None, 5000.0, None, TransportErrorClassification.TIMEOUT)); closures=[]
    with pytest.raises(Exception):
        run(environment={"GOTIME_MOVING_SERVICE_EVAL_ENABLED":"1","GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT":PREFLIGHT_INTENT,"GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY":"x"}, now=NOW,
            active_loader=lambda **kw: active(), client_builder=lambda value: owned,
            transport_factory=lambda client, prepared: transport, output_root=tmp_path,
            closure_operation=lambda **kw: closures.append(kw) or {"authorization_closed": True})
    assert transport.calls == 1 and owned.closed and closures[0]["reason"] == "bounded_failure"
