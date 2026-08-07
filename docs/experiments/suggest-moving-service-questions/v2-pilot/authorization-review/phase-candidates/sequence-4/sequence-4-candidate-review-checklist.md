# Sequence-4 preflight candidate review

- Verify candidate and sequence-4 manifest SHA-256 digests.
- Verify run series `moving-service-stage-b-v2-pilot-20260802`, sequence `4`, fixture `storage_unknown`, and audit prefix `004-storage_unknown`.
- Verify one credential lookup, one client construction, one token preflight, zero generation requests, and zero retries.
- Verify the five-second timeout, 500-token ceiling, and `$0.03` spend ceiling.
- Verify formal evaluation, Stage C, production, FastAPI, frontend, recurring, and background permissions are false.
- Verify all human approval placeholders remain unresolved in the committed candidate.
- Verify sequences 1, 2, and 3 remain consumed historical non-authority.
- Verify the committed execution manifest remains permanently closed.

Outcomes: approve, reject, or request changes. Candidate approval does not activate authority.
