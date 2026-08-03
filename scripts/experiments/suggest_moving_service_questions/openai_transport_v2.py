"""Thin frozen-v2 verifier around the reviewed OpenAI transport mechanics."""

from __future__ import annotations

from decimal import Decimal

from openai_transport import (
    OPENAI_MODEL_IDENTIFIER,
    OpenAIMovingServiceEvaluationTransport,
    OpenAITransportArtifactError,
    VerifiedOpenAITransportArtifacts,
    _without_titles,
    load_verified_openai_transport_artifacts,
)
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v2_pilot import PreparedV2Pilot


class OpenAIV2MovingServiceEvaluationTransport(
    OpenAIMovingServiceEvaluationTransport
):
    """Reuse reviewed provider calls while enforcing the frozen v2 package."""

    def __init__(self, *, client: object, prepared: PreparedV2Pilot, clock=None) -> None:
        kwargs = {"client": client}
        if clock is not None:
            kwargs["clock"] = clock
        super().__init__(**kwargs)
        self.prepared = prepared

    def _verified(
        self, request: MovingServiceProviderRequest
    ) -> VerifiedOpenAITransportArtifacts:
        base = load_verified_openai_transport_artifacts()
        pilot = self.prepared.pilot_configuration
        if request != self.prepared.provider_request:
            raise OpenAITransportArtifactError("V2 request is not the prepared request.")
        if (
            request.model_identifier != OPENAI_MODEL_IDENTIFIER
            or request.model_identifier != pilot["identity"]["ai_model_identifier"]
            or pilot["identity"]["provider"] != "OpenAI"
        ):
            raise OpenAITransportArtifactError("V2 AI model identifier drifted.")
        if dict(request.model_parameters) != {"temperature": 0}:
            raise OpenAITransportArtifactError("V2 model parameters drifted.")
        if (
            request.maximum_output_tokens
            != pilot["model_parameters"]["maximum_output_tokens"]
            or request.retry_count != pilot["transport"]["automatic_retries"]
        ):
            raise OpenAITransportArtifactError("V2 request limits drifted.")
        if request.timeout_seconds != pilot["transport"]["ai_generation_timeout_seconds"]:
            raise OpenAITransportArtifactError("V2 generation timeout drifted.")
        if _without_titles(request.response_json_schema) != _without_titles(
            self.prepared.provider_request.response_json_schema
        ):
            raise OpenAITransportArtifactError("V2 response schema drifted.")
        if pilot["transport"] != {
            "token_preflight_endpoint": "/v1/responses/input_tokens",
            "token_preflight_timeout_seconds": 5,
            "generation_endpoint": "/v1/responses",
            "ai_generation_timeout_seconds": 12,
            "automatic_retries": 0,
            "structured_output_mode": "strict_json_schema",
            "exact_provider_token_preflight_required": True,
            "fresh_preflight_for_exact_generation_request_required": True,
        }:
            raise OpenAITransportArtifactError("Frozen v2 transport settings drifted.")
        return VerifiedOpenAITransportArtifacts(
            response_schema=request.response_json_schema,
            preflight_timeout_seconds=pilot["transport"]["token_preflight_timeout_seconds"],
            generation_timeout_seconds=pilot["transport"]["ai_generation_timeout_seconds"],
            maximum_per_call_spend=Decimal(pilot["limits"]["maximum_total_spend_usd"]),
            uncached_input_price_per_million=base.uncached_input_price_per_million,
            cached_input_price_per_million=base.cached_input_price_per_million,
            output_price_per_million=base.output_price_per_million,
        )

    def _common_input(self, request, artifacts):
        value = super()._common_input(request, artifacts)
        value["text"]["format"]["name"] = "moving_service_question_response_v2"
        return value

    def request_fingerprint(self, request: MovingServiceProviderRequest) -> str:
        """Expose the reviewed payload fingerprint to the evidence binder."""
        return self._request_fingerprint(request, self._verified(request))


def make_v2_openai_transport(client: object, prepared: PreparedV2Pilot):
    """Capability-specific factory for dependency-injected clients."""
    return OpenAIV2MovingServiceEvaluationTransport(client=client, prepared=prepared)
