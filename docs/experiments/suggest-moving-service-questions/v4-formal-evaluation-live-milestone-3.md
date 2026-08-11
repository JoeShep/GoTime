# Architecture A Milestone 3 — AI Case Envelopes

## Scope and identity

Milestone 3 adds immutable, non-authoritative envelopes for exactly the eight
frozen AI cases. The envelope schema is
`suggest-moving-service-questions-v4-formal-evaluation-ai-case-envelope-v1`,
version 1. The aggregate identity, version, and package digest remain unchanged.

Each envelope separates `immutable_binding`, which determines
`envelope_sha256`, from inactive `phase_lifecycle` placeholders. No timestamp
or mutable aggregate state enters the envelope identity.

The immutable binding contains the aggregate/package and evaluation-set
identities; case ID and deterministic case-input digest; deterministic request,
canonical-attempt, and provider-fingerprint triple; frozen-v4 manifest; prompt,
request/response schema, and provider-schema identities; provider, pinned model,
and SDK; frozen model/transport request configuration; one-preflight,
one-generation, zero-retry, `$0.03` case policy; and explicit false spending and
provider authority.

Inactive lifecycle fields start as `preflight_status=not_authorized`,
`generation_status=not_authorized`, zero provider attempts, nonterminal,
not-started review, no applicable evidence deletion, and open coordination
closure. These fields describe no grant and cannot dispatch anything.

## Exact envelopes

The stable AI order and envelope digests are:

- `eval-v4-01`: `bf232c80e3fbb649b3305dfe5417dc944c25c6d2e451fa0f13844d448dfdef46`
- `eval-v4-02`: `ae4ce191cd2f080e35cb6d3e6fd283b524c58c5bffaeef3d8899ea05385e9929`
- `eval-v4-03`: `d287d246d7ce8626f76ef8319fb02cfd2f1a6544f36ba8cb288ffa2c2139cd57`
- `eval-v4-04`: `5af8c886d6259c0f9cc69b5302d146303b7a0b1571dcc99fb8a08174070d2428`
- `eval-v4-05`: `ccff5e2ad61e42e658368f003ca7627be0988b52004835a95b43293af890b33a`
- `eval-v4-06`: `431cf7816ba21afe8975af79f74a7069103bb47d3f3aa7b4e1c118f4b1cc3244`
- `eval-v4-09`: `99446161c6e4a60f2061d9cc18afef57a548db3ad5671659f95175e0a0bbe75e`
- `eval-v4-10`: `5b9145dd1c24994f5ab158b42618cd343135b0cfa42f6b1f8fec99c337d9f506`

All eight are unique because their frozen case/request identities differ; no
salt is used. Cases 07/08 reject envelope construction and retain only their
Milestone 2 deterministic terminal outcomes.

## Binding, replay, and recovery

The one-time aggregate operation is `ai_case_envelopes_bound`. It is permitted
only while the aggregate is `in_progress` and after both deterministic cases
are terminal. One event atomically binds the complete eight-envelope map in AI
order. It cannot mutate cases, acknowledgement, expiration, budget, counters,
labels, aggregate identity, or authority. Exact rerun returns the existing state
without an event; incomplete, extra, substituted, or changed envelopes fail.

The event is part of authoritative aggregate history and the projection is
fully replay-derived. If history commits before projection replacement, fresh
load reconstructs all eight exact envelopes without rewriting history or
appending a duplicate event.

Binding at or after the inclusive expiration boundary fails closed. Expiration
after binding preserves every envelope with both phases still unauthorized and
blocks next-case coordination. Reactivation remains Milestone 12 work.

Correctly rehashed attacks cover each component of a cross-case request triple,
whole-envelope swaps, case-input/provider/model/manifest/ceiling drift,
duplicate digest, missing/extra envelope, and attachment to a deterministic
case. Replay rejects them by exact semantic equality with frozen bindings.

## Commands and deferred work

The public offline inventory is seven commands:

- `verify-foundation`
- `initialize`
- `inspect`
- `verify`
- `resolve-deterministic-cases`
- `bind-ai-case-envelopes`
- `close`

The binding command accepts no case, identity, provider, or configuration
override. The exact flow resumes the aggregate, resolves 07/08, binds all eight
envelopes, inspects/verifies from fresh processes, and closes rehearsal state by
explicit abandonment. It reads no credential and creates no client, network
operation, preflight, generation, grant, reservation, or spending authority.

Milestones 4 and 7 own phase grants, Milestone 5 owns prospective accounting,
Milestone 6 owns dispatch consumption, and Milestone 8 owns the credential
boundary. Milestones 11 and 12 remain acknowledgement and extension owners.
