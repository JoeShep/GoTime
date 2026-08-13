# Post-Milestone-9 framework reassessment

Date: 2026-08-13

Status: design recommendation awaiting human review. No runtime, test,
framework, frozen-artifact, provider, credential, or live-authorization change
is part of this reassessment.

## Decision

Recommendation: `freeze_ai_infrastructure_and_return_to_product`.

GoTime does not currently need another workflow/control-plane layer beyond the
bounded formal-evaluation infrastructure completed through Milestone 9. Do not
adopt Temporal, Inngest, or LangGraph now, and do not continue directly into
Milestone 10. Preserve the experiment in its permanent
`closed_no_execution_authorized` state and return engineering effort to the
GoTime MVP.

This is not a judgment that durable workflow infrastructure has no future
value. It is a timing decision. The product has not yet demonstrated multiple
long-running production workflows, unattended durable waits, worker
coordination, or operational pain that would repay migration. Meanwhile, the
MVP still needs product fundamentals such as durable user data, richer goal and
task workflows, and a stronger answer to “What should I do next?” Investing in
those areas has more immediate user value than completing an offline AI
evaluation control plane.

The historical build-vs-adopt review and digested implementation plan remain
unchanged. Their `defer_adoption` decision carried the custom Architecture A
implementation through Milestone 9 and required this checkpoint. This record
is the post-checkpoint disposition: no adoption and no additional custom AI
control-plane implementation for now.

## What Milestones 1–9 already provide

The completed custom implementation is sufficient to preserve and inspect the
experiment safely offline:

- authoritative hash-chained history, semantic replay, projection recovery,
  and fail-closed crash states;
- deterministic non-AI handling and immutable case, envelope, request,
  attempt, grant, and reservation identities;
- prospective case/aggregate budget accounting and irreversible operation-slot
  consumption;
- one `provider_dispatch_started` boundary immediately before provider entry;
- fixed same-shell credential handling, source-script refusal, and no secret in
  argv or durable state;
- zero workflow, application, SDK, and GoTime-controlled transport retries;
- canonical preflight result validation, bounded evidence, and explicit human
  preflight-evidence approval before generation eligibility;
- canonical generation validation, bounded diagnostics/evidence, independent
  provider-phase closure, and a fail-closed Milestone 10 handoff; and
- ADR-0005 retained-head integrity semantics and a permanent closed live
  authorization state.

These are the hard GoTime-specific guarantees. A framework could host them but
would not eliminate their identity, budget, dispatch, review, validation,
fallback, privacy, or closure policy.

## Gaps that materially matter now

The remaining experiment gaps are real but not currently product blockers:

- validated generation evidence has no implemented human review, deletion, or
  24-hour deadline lifecycle;
- there is no unattended durable timer/scheduler for that deadline;
- hard-gate acknowledgement, aggregate extension, and richer cross-session
  operator coordination remain unimplemented;
- the incremental event model has not been consolidated into the planned final
  live-evaluation specification and proof package; and
- no live-readiness package or live authority exists.

Those gaps matter before a live formal evaluation, especially evidence privacy
and deadline enforcement. They do not justify operating a workflow framework
or finishing the full control plane before GoTime has a demonstrated product
need for the AI capability.

No additional implementation is required to park the experiment safely. The
minimum parking action is this reviewed decision record: retain the committed
tests and artifacts, keep the permanent manifest closed, create no live state,
and leave the next-case/evidence lifecycle unexecuted.

## Options reassessed

### Continue custom Architecture A now

This has the lowest migration risk and preserves the exact semantics already
proved. It is technically viable for Milestones 10–18, but it now has the wrong
opportunity cost. The remaining work is dominated by deadline enforcement,
operator lifecycle, extensions, consolidation, rehearsal, and proof rather
than new user value. Continuing would also increase the risk that experimental
JSON workflow infrastructure becomes an accidental product platform.

Disposition: do not continue now; preserve it as a bounded experiment.

### Adopt Temporal now

Temporal offers the strongest generic durability, crash recovery, long-lived
execution, timers, and workflow history. Its official documentation describes
execution that resumes after process or infrastructure failure and supports
self-hosted or managed deployment
([Temporal documentation](https://docs.temporal.io/)). It would be the leading
candidate if GoTime later has several mission-critical, long-running workflows.

Today it would require a workflow/activity migration, workers, service or cloud
operations, deployment/versioning practices, and careful preservation of the
custom consumed-before-provider and zero-retry rules. It would replace working
experimental replay/timer plumbing before those capabilities are needed by the
product. The migration cost and operational surface are not justified for one
paused evaluation.

Disposition: do not adopt now.

### Adopt Inngest now

Inngest supplies checkpointed steps, durable waits, event-driven resumption,
and independent step retry/recovery
([Inngest steps](https://www.inngest.com/docs/learn/inngest-steps),
[wait for event](https://www.inngest.com/docs/features/inngest-functions/steps-workflows/wait-for-event)).
It is operationally attractive if future GoTime features become event-driven
reminders, scheduled follow-ups, or approval waits.

The present workflow is a tiny, fixed, operator-driven state machine. Moving it
to event/step semantics would add a hosted or self-hosted dependency and require
explicit suppression/auditing of retry behavior while leaving GoTime's
permanent identities, budgets, dispatch boundary, and evidence rules intact.
No near-term user workflow presently needs that trade.

Disposition: do not adopt now.

### Adopt LangGraph now

LangGraph provides checkpoint persistence, replay, interrupts, and human-in-the-
loop resumption
([persistence](https://docs.langchain.com/oss/python/langgraph/persistence),
[interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)). A
durable production checkpointer is still required, and replay or resumed nodes
need disciplined side-effect/idempotency design. Its graph vocabulary is most
valuable for stateful agent or branching model workflows.

GoTime deliberately has one bounded provider capability inside a deterministic
core, not an agent graph. LangGraph would introduce an AI-oriented execution
abstraction without replacing the reviewed authorization and dispatch policy,
and its own documentation notes that replay can re-trigger downstream LLM/API
steps. That is a poor fit for the one-attempt provider boundary unless GoTime
continues to own the same safeguards.

Disposition: do not adopt now.

### Freeze and return to the MVP

This option has no migration cost, adds no services, keeps operating cost at
zero for the paused experiment, and preserves all learned policy and tests. It
also directs work toward the product areas that can establish whether users
actually need this AI capability or any durable workflow platform.

Disposition: recommended.

## Remaining Milestones 10–18

The committed numbering and plan are not changed by this assessment.

| Milestone | Current assessment | Reason |
|---|---|---|
| 10 — generation-evidence review/deletion/deadline | Necessary before a live generated-response evaluation; defer while parked | It closes the present privacy/human-review handoff. It is not needed to preserve the closed offline experiment. |
| 11 — hard-gate acknowledgement | Useful but conditional/deferrable | Needed only after an applicable terminal hard-gate outcome and continued evaluation. |
| 12 — aggregate extension | Deferrable and likely unnecessary for a first bounded run | A seven-day extension mechanism has no value while no aggregate is live. |
| 13 — pause/resume across sessions | Largely already supported at the history/replay layer; richer orchestration is deferrable | Build only if real multi-session operation demonstrates a gap. |
| 14 — consolidated aggregate history/state model | Useful consolidation, but reducible | Milestones 1–9 already implement and test most event/replay semantics incrementally. Consolidate only if the experiment resumes toward live readiness. |
| 15 — operator command surface | Deferrable/reducible | Fixed provider launchers and the ten-command coordination CLI already cover reviewed boundaries; more polish is justified only for an actual operator run. |
| 16 — exact-command full rehearsal | Necessary immediately before live readiness, not now | Evidence goes stale relative to code and environment; rehearse when a live test is actually proposed. |
| 17 — Architecture A proof checkpoint | Necessary under the current plan before live readiness; potentially smaller after rescoping | Much proof already exists, but a final committed-state review remains valuable if live work resumes. |
| 18 — live-readiness package | Strictly necessary before any live provider operation; not authorized now | It is the explicit authority boundary and must remain absent while the experiment is frozen. |

Under the unchanged historical plan, Milestones 10–17 remain prerequisites to
Milestone 18. This reassessment does not silently bypass them. If product
evidence later justifies a live evaluation, first perform a human-reviewed scope
refresh that decides whether the remaining milestones can be reduced while
preserving the same safety properties. Until then, none is the minimum
justified next implementation step.

## Revisit triggers

Revisit framework adoption only when at least one concrete condition exists:

- two or more production capabilities need the same long-lived durable
  orchestration rather than a single paused evaluation;
- unattended timers, reminders, approvals, or multi-day waits become a real
  product requirement;
- concurrent users/workers make the custom file-backed experiment unsuitable;
- custom recovery, scheduling, and operator support produce measurable
  maintenance or incident burden;
- an explicitly approved live evaluation resumes and the refreshed remaining
  plan demonstrates that a framework removes more infrastructure than it adds;
  or
- product persistence and authentication architecture is selected, providing
  a real deployment context in which to judge a durable runtime.

The next reassessment should be trigger-based, not calendar-based. A useful
checkpoint is after the MVP demonstrates a real durable workflow need or
immediately before unfreezing this AI evaluation for live-readiness work.

## Product direction

GoTime should now return to MVP/product development. The next product planning
session should prioritize the smallest user-visible improvement to deciding
what to do next, while separately deciding product persistence when justified.
The frozen AI experiment remains evidence that a bounded capability can be
operated safely; it should not dictate the product's workflow platform before
the product demonstrates that need.
