# OpenAI Response-Schema Review — V4

```text
capability: suggest_moving_service_questions
freeze date: 2026-08-07
source: MovingServiceQuestionResponseV4.model_json_schema()
provider snapshot: openai-response-schema.json
status: reviewed_and_frozen
runtime Pydantic validation authoritative: true
```

The Pydantic response schema is GoTime's authoritative response contract. Its
generated JSON Schema was adapted for OpenAI strict Structured Outputs by
recursively removing only `title` annotations. Definitions, references,
required fields, types, literals, enums, string-length limits, array limits,
and `additionalProperties: false` remain unchanged.

Mechanical formatting changes are allowed, but no required field, type,
allowed value, length limit, array limit, or extra-field prohibition may be
removed, weakened, or broadened. Runtime structural and capability-specific
semantic and prose validation remain authoritative after generation.

## Field review

| Scope | Field | Required | Preserved contract |
| --- | --- | ---: | --- |
| Response | `capability` | Yes | String and exact capability literal |
| Response | `prompt_version` | Yes | String and exact v4 prompt literal |
| Response | `schema_version` | Yes | String and exact v4 schema literal |
| Response | `suggestions` | Yes | Array, maximum three, referenced suggestion object |
| Response | `fallback_recommended` | Yes | Boolean; prompt-v4 false policy is validated separately |
| Response | `warnings` | Yes | String array, maximum five; prompt-v4 empty policy is validated separately |
| Suggestion | `question_id` | Yes | String, length 1–120 |
| Suggestion | `question` | Yes | String, length 1–240 |
| Suggestion | `why_it_matters` | Yes | String, length 1–400 |
| Suggestion | `information_it_would_clarify` | Yes | String, length 1–160 |
| Suggestion | `affected_decision_id` | Yes | String, length 1–120 |
| Suggestion | `selected_missing_information_category` | Yes | Reference and full category enum |
| Suggestion | `relevant_knowledge_ids` | Yes | String array, 1–4 items |
| Suggestion | `grounding_summary` | Yes | String, length 1–500 |
| Suggestion | `reason_not_deterministic` | Yes | String, length 1–300 |
| Suggestion | `uncertainties` | Yes | String array, 0–5 items |
| Suggestion | `suggested_answer_type` | Yes | Reference and full answer-type enum |
| Suggestion | `requires_user_confirmation` | Yes | Boolean literal `true` |

Both response and suggestion objects retain `additionalProperties: false`.
The snapshot adds no field and changes no field meaning. Exact grounding,
known-state checks, supplied-knowledge checks, uniqueness rules, prose checks,
warnings and fallback policy, and human grounding review remain outside the
provider schema and are enforced by GoTime's reviewed evaluation boundary.
