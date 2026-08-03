# V2 Phase-Candidate Review Checklist

Review preflight and generation independently. For each phase, record exactly
one outcome: `approve`, `reject`, or `request_changes`. Approval of one phase
does not approve the other and does not activate repository authority.

## Shared checks

- [ ] Candidate digest matches the phase-candidate manifest.
- [ ] Umbrella digest is `cee4cdb826452906ea677785b1b76cf43745d28237a791d4c129175a0447062a`.
- [ ] Frozen-v2 paths, identities, and exact-byte digests verify.
- [ ] Run series is `moving-service-stage-b-v2-pilot-20260802`.
- [ ] Sequence is `1`; fixture is `storage_unknown`.
- [ ] Provider is OpenAI; AI model identifier is `gpt-4.1-mini-2025-04-14`.
- [ ] SDK pin is `openai==2.45.0`.
- [ ] Credential variable and operator-intent requirement are exact.
- [ ] Retry count is zero; timeouts are 5 seconds and 12 seconds.
- [ ] Maximum output is 500 tokens; total pilot spend is at most $0.03.
- [ ] Approver, reason, and whole-second UTC timestamps are resolved.
- [ ] Active duration is no more than 900 seconds.
- [ ] Single-use, cancellation, expiration, and permanent-closure rules are accepted.
- [ ] Formal evaluation, Stage C, production, FastAPI, frontend, recurring, and background use remain false.

## Preflight-only checks

- [ ] Phase is `preflight`.
- [ ] Limits are one credential lookup, one client construction, one preflight, and zero generations.
- [ ] No generation evidence or generation authority is present.
- [ ] Preflight audit, evidence, review, and closure paths are conflict-free.
- [ ] Outcome: `approve` / `reject` / `request_changes`.

## Generation-only checks

- [ ] Phase is `generation`.
- [ ] Limits are one credential lookup, one client construction, zero preflights, and one generation.
- [ ] Evidence and review file digests match exact owner-only files.
- [ ] Input token count, conservative cost, request digest, canonical-attempt digest, and provider fingerprint match.
- [ ] Preflight reviewer and review timestamp match an approved review.
- [ ] Evidence is fresh, approved, and unused.
- [ ] Response-evidence deletion and generation closure paths are conflict-free.
- [ ] Outcome: `approve` / `reject` / `request_changes`.
