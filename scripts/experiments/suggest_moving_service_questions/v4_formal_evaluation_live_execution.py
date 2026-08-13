"""Milestone 8 same-process provider boundary; production remains fail-closed."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping

from openai_client_factory import (
    OPENAI_SDK_VERSION,
    MovingServiceOpenAIClient,
    _construct_openai_client,
    _read_evaluation_credential,
)
from v4_formal_evaluation_live_generation import generation_grant_is_expired
from v4_formal_evaluation_live_models import MAX_RETRIES
from v4_formal_evaluation_live_preflight_result import PreflightResultError
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, parse_time

CREDENTIAL = "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY"
SDK_PIN = "openai==2.45.0"


class ExecutionBoundaryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedEntry:
    phase: str
    case_id: str
    timeout_seconds: int
    request_configuration: Mapping[str, object]
    envelope_sha256: str
    grant_sha256: str
    reservation_sha256: str
    deterministic_request_sha256: str
    canonical_attempt_sha256: str
    provider_fingerprint: str


class ProviderExecutionBoundary:
    """Internal boundary. Only test subclasses can satisfy live readiness/provider entry."""

    def __init__(self, store: AggregateStore, environment: Mapping[str, str] = os.environ):
        self.store, self.environment = store, environment

    def _live_readiness_authorized(self, phase: str, state: Mapping[str, object]) -> bool:
        return False  # Milestone 18 owns the future durable authorization package.

    def _enter_provider(self, prepared: PreparedEntry, client: object) -> object:
        raise ExecutionBoundaryError("provider entry is unavailable without the future live package")

    def _client_constructors(self) -> tuple[Callable[..., object], Callable[..., object]]:
        """Import the pinned SDK only after credential-free readiness succeeds."""
        from openai import DefaultHttpxClient, OpenAI

        return OpenAI, DefaultHttpxClient

    def _prepare_client(self, prepared: PreparedEntry) -> MovingServiceOpenAIClient:
        """Use the one reviewed factory; construction performs no provider operation."""
        client_constructor, http_client_constructor = self._client_constructors()
        credential = _read_evaluation_credential(self.environment)
        return _construct_openai_client(
            credential,
            sdk_version=OPENAI_SDK_VERSION,
            client_constructor=client_constructor,
            http_client_constructor=http_client_constructor,
        )

    def precheck(self, phase: str) -> PreparedEntry:
        state = self.store.load(observe_expiry=False); case_id = state.get("next_case_id")
        if phase not in {"preflight", "generation"}:
            raise ExecutionBoundaryError("provider phase is unavailable")
        if phase == "generation" and not state["reviewed_preflight_evidence"].get(case_id):
            raise ExecutionBoundaryError("reviewed production preflight evidence is unavailable")
        if not self._live_readiness_authorized(phase, state):
            raise ExecutionBoundaryError("live provider execution authorization is unavailable")
        if self.store.clock() >= parse_time(state["expires_at"]):
            raise ExecutionBoundaryError("aggregate expired before provider entry")
        envelope = state["ai_case_envelopes"].get(case_id)
        if envelope is None or state["counters"]["retries"] != MAX_RETRIES:
            raise ExecutionBoundaryError("exact provider entry state is unavailable")
        binding = envelope["immutable_binding"]
        transport = binding["request_configuration"]
        if transport["automatic_retries"] != 0 or binding["sdk"] != SDK_PIN:
            raise ExecutionBoundaryError("frozen SDK or retry policy drifted")
        key = case_id if phase == "preflight" else f"{case_id}:generation"
        reservation = state["provider_budget_reservations"].get(key)
        if reservation is None:
            raise ExecutionBoundaryError("exact provider reservation is unavailable")
        lifecycle = reservation["lifecycle"]
        if lifecycle["status"] == "released":
            raise ExecutionBoundaryError("provider reservation was released")
        if lifecycle["attempt_consumed"] is True:
            raise ExecutionBoundaryError("provider attempt is already consumed")
        if lifecycle["provider_dispatch_status"] != "not_started":
            raise ExecutionBoundaryError("provider dispatch is already started")
        if lifecycle["status"] != "reserved":
            raise ExecutionBoundaryError("exact reserved provider attempt is unavailable")
        if phase == "generation":
            grant = state["generation_grants"].get(case_id)
            if grant is None or generation_grant_is_expired(grant, self.store.clock()):
                raise ExecutionBoundaryError("reviewed generation authority is unavailable")
            timeout = transport["generation_timeout_seconds"]
        else:
            grant = state["preflight_grants"].get(case_id)
            if grant is None or self.store.clock() >= parse_time(grant["immutable_binding"]["expires_at"]):
                raise ExecutionBoundaryError("active preflight authority is unavailable")
            timeout = transport["token_preflight_timeout_seconds"]
        return PreparedEntry(
            phase, case_id, timeout, binding["request_configuration"],
            envelope["envelope_sha256"], grant["grant_sha256"],
            reservation["reservation_sha256"], binding["deterministic_request_sha256"],
            binding["canonical_attempt_sha256"], binding["provider_fingerprint"],
        )

    def execute_preflight(self) -> object:
        prepared = self.precheck("preflight")
        if not self.environment.get(CREDENTIAL):
            raise ExecutionBoundaryError("evaluation credential is unavailable")
        client = self._prepare_client(prepared)
        with client:
            # Final validation is deliberately after credential acquisition/client preparation.
            if self.precheck("preflight") != prepared:
                raise ExecutionBoundaryError("provider entry state changed during credential acquisition")
            consumed = self.store.record_provider_dispatch_started()
            if consumed["provider_budget_reservations"][prepared.case_id]["lifecycle"]["status"] != "consumed":
                raise AggregateStateError("durable dispatch did not consume the attempt")
            try:
                outcome = self._enter_provider(prepared, client)
            except TimeoutError:
                self.store.record_preflight_failure("timeout")
                raise
            except (ConnectionError, OSError):
                self.store.record_preflight_failure("transport_error")
                raise
            except Exception:
                self.store.record_preflight_failure("provider_error")
                raise
            if (not isinstance(outcome, dict) or set(outcome) != {"input_tokens"}
                    or not isinstance(outcome["input_tokens"], int)
                    or isinstance(outcome["input_tokens"], bool)):
                self.store.record_preflight_failure("invalid_result")
                raise ExecutionBoundaryError("preflight provider result structure is invalid")
            try:
                self.store.record_preflight_success(outcome["input_tokens"])
            except PreflightResultError as error:
                self.store.record_preflight_failure("invalid_result")
                raise ExecutionBoundaryError("preflight provider token-count result is invalid") from error
            return outcome
