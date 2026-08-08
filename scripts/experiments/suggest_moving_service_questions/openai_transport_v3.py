"""Injected-client transport verifier for the frozen-v3 offline gate."""

from __future__ import annotations

from decimal import Decimal

from openai_transport import (
    OPENAI_MODEL_IDENTIFIER,
    OpenAIMovingServiceEvaluationTransport,
    OpenAITransportArtifactError,
    VerifiedOpenAITransportArtifacts,
    load_verified_openai_transport_artifacts,
)
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v2_pilot import PreparedV2Pilot


class OpenAIV3MovingServiceEvaluationTransport(OpenAIMovingServiceEvaluationTransport):
    def __init__(self, *, client: object, prepared: PreparedV2Pilot, clock=None) -> None:
        kwargs = {"client": client}
        if clock is not None:
            kwargs["clock"] = clock
        super().__init__(**kwargs)
        self.prepared = prepared

    def _verified(self, request: MovingServiceProviderRequest) -> VerifiedOpenAITransportArtifacts:
        base = load_verified_openai_transport_artifacts()
        pilot = self.prepared.pilot_configuration
        if request != self.prepared.provider_request:
            raise OpenAITransportArtifactError("V3 request is not the verified request")
        if request.model_identifier != OPENAI_MODEL_IDENTIFIER:
            raise OpenAITransportArtifactError("V3 model identifier drifted")
        if dict(request.model_parameters) != {"temperature": 0}:
            raise OpenAITransportArtifactError("V3 model parameters drifted")
        if request.maximum_output_tokens != 500 or request.retry_count != 0:
            raise OpenAITransportArtifactError("V3 request limits drifted")
        if request.timeout_seconds != 12:
            raise OpenAITransportArtifactError("V3 generation timeout drifted")
        if request.response_json_schema != self.prepared.provider_request.response_json_schema:
            raise OpenAITransportArtifactError("V3 provider schema drifted")
        return VerifiedOpenAITransportArtifacts(
            response_schema=request.response_json_schema,
            preflight_timeout_seconds=5,
            generation_timeout_seconds=12,
            maximum_per_call_spend=Decimal(pilot["limits"]["maximum_total_spend_usd"]),
            uncached_input_price_per_million=base.uncached_input_price_per_million,
            cached_input_price_per_million=base.cached_input_price_per_million,
            output_price_per_million=base.output_price_per_million,
        )

    def _common_input(self, request, artifacts):
        value = super()._common_input(request, artifacts)
        value["text"]["format"]["name"] = "moving_service_question_response_v3"
        return value

    def request_fingerprint(self, request: MovingServiceProviderRequest) -> str:
        return self._request_fingerprint(request, self._verified(request))


def make_v3_openai_transport(client: object, prepared: PreparedV2Pilot):
    return OpenAIV3MovingServiceEvaluationTransport(client=client, prepared=prepared)
