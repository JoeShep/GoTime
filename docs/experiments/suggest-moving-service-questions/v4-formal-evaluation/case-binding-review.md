# Frozen-v4 formal-evaluation case-binding review

Evaluation-set ID: `suggest-moving-service-questions-v4-formal-evaluation-set-v1`.

All ten approved cases validate through the existing frozen-v4 domain and request schemas. Cases 1–6, 9, and 10 are generation-eligible. Case 7 uses `known(false)` and case 8 uses the existing `not_applicable` status; both are deterministically empty before provider-request construction.

The eight provider-eligible cases bind literal deterministic-request, canonical-attempt, and provider-fingerprint digests. The empty cases bind null provider identities rather than invented hashes. Frozen v4, validator, fallback, and runtime reachability are unchanged.

The manifest-bound `execution-budget.json` explicitly supersedes only the plan's provisional live-call budget. Future maximums are eight token preflights, eight generations, zero retries, and a `$0.24` aggregate provider ceiling. All other plan requirements and graduation criteria remain unchanged. This record authorizes no provider operation.
