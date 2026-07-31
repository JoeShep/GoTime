# OpenAI Response-Schema Review

```text
capability: suggest_moving_service_questions
review date: 2026-07-31
source: MovingServiceQuestionResponse.model_json_schema()
provider snapshot: openai-response-schema.json
status: reviewed_and_frozen
runtime Pydantic validation authoritative: true
```

The Pydantic response schema is GoTime's authoritative response contract. Its
generated JSON Schema was adapted for OpenAI Structured Outputs by recursively
removing only `title` annotations. Definitions, references, required fields,
types, literals, enums, string-length limits, array limits, and
`additionalProperties: false` were preserved unchanged.

Mechanical formatting changes are allowed, but no required field, type,
allowed value, length limit, array limit, or extra-field prohibition may be
removed, weakened, or broadened.

## Field Review

| Scope | Field | Required | Preserved contract |
| --- | --- | ---: | --- |
| Response | `capability` | Yes | String and exact capability literal preserved |
| Response | `prompt_version` | Yes | String and exact prompt-version literal preserved |
| Response | `schema_version` | Yes | String and exact schema-version literal preserved |
| Response | `suggestions` | Yes | Array, maximum three, referenced suggestion object preserved |
| Response | `fallback_recommended` | Yes | Boolean preserved; prompt-v1 false policy remains runtime-validated |
| Response | `warnings` | Yes | String array and maximum five preserved; prompt-v1 empty policy remains runtime-validated |
| Suggestion | `question_id` | Yes | String, length 1–120 preserved |
| Suggestion | `question` | Yes | String, length 1–240 preserved |
| Suggestion | `why_it_matters` | Yes | String, length 1–400 preserved |
| Suggestion | `information_it_would_clarify` | Yes | String, length 1–160 preserved |
| Suggestion | `affected_decision_id` | Yes | String, length 1–120 preserved |
| Suggestion | `selected_missing_information_category` | Yes | Reference and full category enum preserved |
| Suggestion | `relevant_knowledge_ids` | Yes | String array, 1–4 items preserved |
| Suggestion | `grounding_summary` | Yes | String, length 1–500 preserved |
| Suggestion | `reason_not_deterministic` | Yes | String, length 1–300 preserved |
| Suggestion | `uncertainties` | Yes | String array, 0–5 items preserved |
| Suggestion | `suggested_answer_type` | Yes | Reference and full answer-type enum preserved |
| Suggestion | `requires_user_confirmation` | Yes | Boolean literal `true` preserved |

Both response and suggestion objects retain `additionalProperties: false`.
The snapshot adds no field and changes no field meaning. Cross-field rules,
known-state checks, supplied-knowledge checks, uniqueness checks, warnings and
fallback policy, and other semantic validation remain the responsibility of
the existing runtime validator.
