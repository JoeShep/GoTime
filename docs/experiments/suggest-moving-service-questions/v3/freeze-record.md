# Prompt V3 Freeze Record

Prompt v3 responds to the consumed live v2 response that passed structure and
semantics but failed storage-modality and service-selection prose checks. The
raw response was not retained. Existing validators remain unchanged; prompt v3
is intentionally stricter in five documented synthetic cases.

Schema v3 changes only prompt/schema literals and generated root titles.
Fallback remains `moving-service-fallback-v2`. No live v3 generation has
occurred. Bounded rejected-prose diagnostics remain a separate future
milestone. Freezing does not authorize credentials, preflight, generation,
formal evaluation, Stage C, production, FastAPI, or frontend use.
