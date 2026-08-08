"""Injected-client fingerprint verifier for the frozen-v4 offline package."""

from __future__ import annotations

from openai_transport_v3 import OpenAIV3MovingServiceEvaluationTransport
from run_openai_stage_b_v2_pilot import PreparedV2Pilot


class OpenAIV4MovingServiceEvaluationTransport(OpenAIV3MovingServiceEvaluationTransport):
    def _common_input(self, request, artifacts):
        value = super()._common_input(request, artifacts)
        value["text"]["format"]["name"] = "moving_service_question_response_v4"
        return value


def make_v4_openai_transport(client: object, prepared: PreparedV2Pilot):
    return OpenAIV4MovingServiceEvaluationTransport(client=client, prepared=prepared)
