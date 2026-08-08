# Prompt V3 Schema-Diff Review

Status: draft and non-authoritative.

The existing v2 request and response classes each bind both
`prompt_version="moving-service-questions-prompt-v2"` and
`schema_version="moving-service-questions-schema-v2"`. Prompt v3 therefore
requires new identity literals to remain fail-closed.

Proposed later implementation:

```text
MovingServiceQuestionRequestV3 extends MovingServiceQuestionRequest
  prompt_version: Literal["moving-service-questions-prompt-v3"]
  schema_version: Literal["moving-service-questions-schema-v3"]

MovingServiceQuestionResponseV3 extends MovingServiceQuestionResponse
  prompt_version: Literal["moving-service-questions-prompt-v3"]
  schema_version: Literal["moving-service-questions-schema-v3"]
```

No field, type, enum, constraint, required-list, model configuration, or
extra-field behavior change is proposed. This milestone does not implement
these classes or create a provider-schema snapshot.

