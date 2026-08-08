"""Offline-only literal-versioned contracts for frozen prompt-v3 artifacts."""

from __future__ import annotations

from typing import Literal

from app.moving_service_questions import (
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
)
from moving_service_questions_v2 import adapt_response_schema_for_openai_v2


PROMPT_VERSION_V3 = "moving-service-questions-prompt-v3"
SCHEMA_VERSION_V3 = "moving-service-questions-schema-v3"


class MovingServiceQuestionRequestV3(MovingServiceQuestionRequest):
    prompt_version: Literal["moving-service-questions-prompt-v3"]
    schema_version: Literal["moving-service-questions-schema-v3"]


class MovingServiceQuestionResponseV3(MovingServiceQuestionResponse):
    prompt_version: Literal["moving-service-questions-prompt-v3"]
    schema_version: Literal["moving-service-questions-schema-v3"]


def adapt_response_schema_for_openai_v3(value: object) -> object:
    """Apply the unchanged title-only strict-provider adaptation."""

    return adapt_response_schema_for_openai_v2(value)
