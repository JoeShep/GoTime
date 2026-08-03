# V2 Follow-Up Pilot Authorization Review Checklist

Status: inactive and non-authoritative. Checking or approving this document
does not activate execution.

- [ ] Frozen v1 integrity passes.
- [ ] Frozen v2 manifest and every bound digest pass.
- [ ] Run series is `moving-service-stage-b-v2-pilot-20260802`.
- [ ] Sequence is exactly `1` and remains unused.
- [ ] Fixture is exactly `storage_unknown`.
- [ ] Provider is OpenAI and AI model identifier is `gpt-4.1-mini-2025-04-14`.
- [ ] SDK pin is `openai==2.45.0`.
- [ ] Credential variable is `GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY`.
- [ ] Operator intent and `GOTIME_MOVING_SERVICE_EVAL_ENABLED=1` are exact.
- [ ] Counts are one credential read, client construction, preflight, and generation.
- [ ] Timeouts are five seconds for preflight and 12 seconds for generation.
- [ ] Retries are zero, output ceiling is 500 tokens, and spend ceiling is $0.03.
- [ ] Human grounding review is mandatory.
- [ ] Approver identity replaces `APPROVER_ID_REQUIRED` without invention.
- [ ] Approval, activation, and expiration are exact UTC whole-second timestamps.
- [ ] Validity is at most 900 seconds and expiration follows activation.
- [ ] Single-use consumption begins at the earliest attempted irreversible stage.
- [ ] Audit, response-evidence, deletion, and closure paths are exact and unused.
- [ ] Evidence deletion occurs at sign-off or within 30 days, whichever is earlier.
- [ ] Stage C, formal evaluation, and production use remain false.

Review outcome (choose exactly one):

- [ ] Approve candidate for a separate activation-package rendering milestone.
- [ ] Reject candidate; leave permanent closed authorization unchanged.
- [ ] Request changes; identify the exact field and rationale before rendering.
