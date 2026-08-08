"""Offline-only literal-versioned contracts for frozen prompt-v4 artifacts."""

from __future__ import annotations

from typing import Literal

from app.moving_service_questions import MovingServiceQuestionRequest, MovingServiceQuestionResponse
from moving_service_questions_v3 import adapt_response_schema_for_openai_v3

PROMPT_VERSION_V4 = "moving-service-questions-prompt-v4"
SCHEMA_VERSION_V4 = "moving-service-questions-schema-v4"


class MovingServiceQuestionRequestV4(MovingServiceQuestionRequest):
    prompt_version: Literal["moving-service-questions-prompt-v4"]
    schema_version: Literal["moving-service-questions-schema-v4"]


class MovingServiceQuestionResponseV4(MovingServiceQuestionResponse):
    prompt_version: Literal["moving-service-questions-prompt-v4"]
    schema_version: Literal["moving-service-questions-schema-v4"]


def adapt_response_schema_for_openai_v4(value: object) -> object:
    """Apply the unchanged title-only strict-provider adaptation."""
    return adapt_response_schema_for_openai_v3(value)
