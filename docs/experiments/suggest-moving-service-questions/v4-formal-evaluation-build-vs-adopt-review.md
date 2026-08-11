# Frozen-v4 Formal Evaluation Build-vs-Adopt Review

## 1. Executive summary

**Approved decision: `defer_adoption`.** Continue the committed custom
Architecture A implementation through Milestones 5–9, while preserving narrow
interfaces around persistence, clocks/timers, prospective budget authorization,
and the future provider-dispatch activity. Do not install or migrate to an
orchestration framework, and do not run an infrastructure proof of concept,
before Milestone 5.

**Runner-up: `stay_custom`.** It has nearly the same near-term advantages but
lacks an explicit trigger to reconsider generic infrastructure. Deferral is the
better decision because it treats the current JSON history/projection machinery
as experimental infrastructure, not an assumed production platform.

The decision is based on five findings:

1. Milestones 5–9 are dominated by GoTime-specific safety policy: prospective
   ceilings, exact grant identity, dispatch consumption, one-attempt semantics,
   unchanged validation/fallback, and closure. No candidate removes that work.
2. Temporal is the strongest technical replacement for generic durability, but
   adopting it now would add migration, learning, worker, persistence, and
   operational concerns before it removes enough GoTime code to justify that
   abstraction cost at friends/family scale.
3. Inngest is operationally attractive and inexpensive at very small scale,
   but its event/step semantics and 24-hour idempotency windows do not replace
   GoTime's permanent case identity, prospective budget, or exact
   `provider_dispatch_started` rule.
4. LangGraph can replace checkpointing and human interrupts, especially with a
   managed LangSmith deployment, but the open-source library leaves production
   persistence, scheduling, deployment, and monitoring to GoTime. It also adds
   an agent-oriented graph abstraction to a deliberately non-agentic product.
5. The OpenAI Agents SDK improves AI/tool invocation, guardrails, approvals,
   resumable run state, and tracing. It explicitly leaves deployment, storage,
   and approval decisions with the application. It is largely orthogonal to the
   durability/control-plane problem and is less direct than the Responses API
   for this one bounded capability.

Direct vendor cost is only one input to this decision. Some candidates have
free or low-cost entry tiers. Engineering cost, maintenance burden,
operational simplicity, migration effort, and abstraction cost carry more
weight for the present phase.

This review does not authorize live state or provider work. The permanent
execution manifest remains `closed_no_execution_authorized`, digest
`18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa`.

## 2. Current-state architecture

### Verified baseline

- Branch: `main`.
- `HEAD` and `origin/main` at review start:
  `b3f59e25528f6d5d29f16e8a84d74ad1847eb93c`.
- Architecture A aggregate:
  `suggest-moving-service-questions-v4-formal-evaluation-live-v1`, version 1,
  package digest
  `1f6b1b979fd1a244489e0782bf4d37854bb1f800cca8dc4f5faeb06cff83699d`.
- Implementation-plan digest:
  `2583a48af17e6ccde57ae3028d3971ed2818ab86d07346d0bff78cdff1422921`.
- Milestones 1–4 are committed. Milestone 5 has not begun.
- The only pre-existing working-tree change at review start was
  `docs/parking-lot.md`; this review did not modify it.

### What Milestones 1–4 actually implement

#### Milestone 1: aggregate coordination

`v4_formal_evaluation_live_models.py` defines the immutable ten-case package,
fixed AI order, seven-day coordination lifetime, zero-retry rule, frozen
budget limits, false spending/provider authority, and zero counters.
`v4_formal_evaluation_live_state.py` implements:

- locked, hash-chained `aggregate-history.json` as authoritative lifecycle
  history;
- replay-derived `aggregate.json` as a projection;
- exact operation-semantic validation, not merely digest validation;
- history-first atomic writes, fsync, stale-projection detection, and unique
  projection reconstruction after interruption;
- inclusive seven-day expiry for prepared, approved, and in-progress state;
- fixed membership/order and deterministic next-AI-case derivation;
- durable fresh-process inspection/resume and fail-closed acknowledgement,
  budget, and provider-counter invariants.

This is useful and carefully tested, but ADR-0005 explicitly says the local
JSON journal is not a product persistence choice or hostile-filesystem security
boundary.

#### Milestone 2: deterministic bypass

`v4_formal_evaluation_live_deterministic.py` delegates eligibility to the
frozen `bind_case` boundary. Cases 07 and 08 close terminally as
`known(false)` and `not_applicable` without entering the provider constructor.
Completion is fixed-order, exactly once, replayable, idempotent on rerun, and
recoverable after a partial 07-only interruption. This is GoTime policy, not
generic workflow infrastructure.

#### Milestone 3: immutable AI envelopes

`v4_formal_evaluation_live_cases.py` creates exactly eight immutable,
case-specific envelopes. Each binds the frozen input, request identity,
canonical attempt, provider fingerprint, provider/model/SDK/configuration,
manifest, case ceiling, and inactive phase state. The atomic
`ai_case_envelopes_bound` event and adversarial tests prevent cross-case
substitution, missing/extra/reordered/duplicate envelopes, or deterministic
case attachment. These identities should survive any infrastructure migration.

#### Milestone 4: preflight grant candidates

`v4_formal_evaluation_live_grants.py` prepares one exact next-case preflight
candidate with a 15-minute inclusive-expiry boundary, single-use/zero-retry
policy, canonical case ceiling, and immutable envelope/request binding. The
production budget port always denies, so no active authority, reservation,
dispatch, credential, client, network, or provider operation exists. Prepared
state is durable and replayable. The grant model is GoTime policy; its journal
storage is generic plumbing.

### Current architecture boundary

The current code is an offline experimental control plane. It has unusually
strong semantic tests for its scope, but it is not a production workflow
service, scheduler, database, queue, authentication system, or external audit
anchor. Continuing Architecture A does not mean treating the current `.local`
files as the eventual product database.

## 3. GoTime policy vs generic infrastructure

### A. Keep GoTime-owned

The following are product/evaluation semantics. A framework may persist their
outcomes, but it must not define them:

- deterministic eligibility before any AI path;
- named bounded capabilities and curated grounding;
- frozen evaluation, case, request, attempt, and provider identities;
- immutable AI envelopes and exact grant binding;
- fixed case order and next-case eligibility;
- semantic/prose validators, deterministic fallback, accepted-result rules,
  evidence semantics, and scoring;
- zero retries and one attempt per case/phase;
- prospective per-case and aggregate budget ceilings;
- the exact point at which `provider_dispatch_started` consumes authority;
- provider uncertainty classification and conservative exposure;
- human confirmation, evidence review/deletion, hard-gate acknowledgement,
  and extension policy;
- independent case closure and final proof/readiness criteria.

These rules should remain plain GoTime domain services and immutable value
objects even if a durable runtime later calls them.

### B. Candidates for delegation

The most replaceable code is generic execution infrastructure:

- durable event/state persistence and checkpoint storage;
- replay, projection reconstruction, and crash recovery;
- durable timers for grant, aggregate, and review deadlines;
- pause/resume and external human-wait state;
- durable state-transition execution and scheduling;
- generic idempotency, with retries explicitly configured to zero;
- worker recovery, operational visibility, tracing, and history retention.

Delegation would reduce total complexity only if it removes GoTime-owned
storage/recovery/timer code without forcing policy into framework-specific
graphs, activities, or event expressions. An abstraction that merely wraps the
same custom lifecycle rules is a net increase.

### Recommended seams now

Without implementing them in this review, future work should keep these
conceptual boundaries narrow:

- `AggregateRepository` or equivalent: append an expected transition and load
  authoritative state without exposing JSON details to policy;
- injected UTC clock and future durable deadline scheduler;
- the existing fail-closed `BudgetAuthorization` port;
- a provider-dispatch activity boundary whose input is the exact immutable
  grant/request and whose first durable GoTime event is consumption;
- framework-neutral serializable policy values and stable frozen digests.

## 4. Candidate analysis

### Option A — `stay_custom`

#### Fit

The custom path best preserves exact semantics, transparent local debugging,
fixed zero-retry behavior, and the lack of model-owned autonomy. Milestones
1–4 already prove the difficult identity, non-entry, replay, expiry, and
substitution invariants. No new service or framework lifecycle competes with
GoTime's state model.

#### Savings and costs

It saves no remaining implementation effort. GoTime must still build budget
transactions, dispatch ambiguity handling, timers, review waits, deletion
recovery, extensions, consolidated replay, and production hardening. The
engineering and adversarial-test burden is real even with no vendor invoice.
The current local approach is simple to run but would need a separate product
persistence decision before public use.

#### What it replaces from Milestones 1–4

Nothing. Everything remains directly reusable. The risk is not sunk work; it
is allowing experimental persistence to accrete into an accidental platform.

### Option B — `adopt_langgraph`

#### Open-source LangGraph

LangGraph is an MIT-licensed, low-level graph runtime that can be used without
LangChain. With a durable checkpointer, it stores checkpoints by thread,
supports fault recovery, time-travel/replay, pending-write recovery, and
interrupt/resume for human input. Nodes are ordinary functions, so GoTime
could carry immutable envelopes as typed state and keep decisions in code.

The open-source library does not by itself provide a production service,
scheduler, monitoring plane, or managed database. Official documentation
distinguishes community/self-managed checkpointers from LangSmith's managed
Postgres and states that open-source scheduling is absent. GoTime would still
select, run, secure, back up, and upgrade a production checkpointer.

Retries are opt-in at nodes in the documented fault-tolerance API; omitting a
retry policy supports zero retries. Care is still required because graph nodes
can replay and side effects before interrupts must be idempotent. The exact
dispatch-consumption seam remains GoTime-owned and should be a small isolated
node/activity, not inferred from a checkpoint.

#### Hosted LangSmith

LangSmith adds managed persistence, APIs, deployment, scaling, and
observability. Current pricing distinguishes a free one-seat Developer tier
from the `$39/seat/month` Plus tier; deployment is a Plus feature with one
small serverless deployment included, then metered compute/storage. This
removes more generic operations but introduces a hosted proprietary platform
and cloud state model.

#### GoTime fit

LangGraph could replace much of Milestone 1's checkpoint/projection recovery
and later pause/resume/human-wait infrastructure. It would not replace frozen
identity, grants, budget, dispatch consumption, validators, fallback, scoring,
or evidence rules. Its graph vocabulary is workable but encourages an
agent-shaped architecture GoTime does not need. The meaningful version of
adoption is hosted LangSmith or a production database-backed checkpointer;
using only in-memory/local checkpoints would not solve the reviewed problem.

### Option C — `adopt_temporal`

#### Technical fit

Temporal is the strongest generic durability candidate. Workflow Event History
is authoritative, deterministic replay reconstructs state, durable timers can
sleep for months without holding a worker, and Signals/Updates support human
intervention. External calls belong in Activities; Workflows remain
deterministic. This maps naturally to one aggregate Workflow, case policy in
Workflow code, and provider calls in tightly bounded Activities.

Temporal Activity retries default to unlimited exponential retries, so GoTime
must explicitly set `maximum_attempts=1` and also distinguish Workflow Task
retries from provider Activity attempts. Temporal documents Activities as
at-least-once: if work succeeds but the worker crashes before reporting it, the
Activity may run again. Therefore Temporal does not automatically solve exact
provider one-attempt semantics. GoTime must still durably consume the grant
before provider entry, pass a stable idempotency identity where supported, and
classify uncertain dispatch conservatively. A Temporal Activity boundary can
host this rule well, but cannot define it for us.

Temporal would largely replace the custom journal, projection, replay engine,
restart recovery, durable timers, long waits, and pause/resume plumbing. It
would partially simplify Milestones 10–14. It would not replace Milestones 5–9
policy.

#### Operations and cost

Local development is good: the CLI development server is one binary with no
external dependency. Production is materially heavier. GoTime must run Worker
processes in either hosting model. Temporal Cloud removes service/database
operations but currently starts at `$100/month` for Essentials, including one
million Actions, active/retained storage allocations, and support; additional
Actions begin at `$50/million`, with active and retained storage metered.

Self-hosting is open source but the documented Docker Compose example includes
Temporal Server, PostgreSQL, Elasticsearch, and Web UI, plus schema upgrades.
Production also needs security, monitoring, visibility, backup, and safe
upgrades. That is excellent infrastructure when durable workflows are a core
product platform and disproportionate for one developer and friends/family
traffic.

### Option D — `adopt_inngest`

#### Technical fit

Inngest functions use checkpointed steps; completed step results are persisted
and later runs resume from the failed step. `step.sleep` and
`step.waitForEvent` provide durable delays and human approval patterns.
Functions/steps retry four times by default but accept `retries: 0`, which is
compatible with GoTime only if every provider-bearing function and step is
audited explicitly.

The event-driven model is natural for future reminders, deadlines, background
evidence-review expiry, and multi-topic planning notifications. It is less
natural for the current tightly ordered operator evaluation, where a single
state machine and exact before/after semantic replay are easier to audit than
fan-out event handlers.

Inngest idempotency helps but does not replace GoTime's permanence: documented
event and function idempotency keys deduplicate for 24 hours. GoTime's case and
attempt non-reuse lasts for the evaluation history. The provider dispatch must
still be one step that validates and persists GoTime consumption immediately
before the call; a checkpointed step cannot eliminate the external
uncertain-result gap. Budget reservation remains a GoTime transaction.

#### Operations and cost

Managed Inngest has the simplest hosted small-scale entry: the Hobby tier is
currently `$0/month` with 50,000 executions and five concurrent executions;
Pro starts at `$99/month` with one million or more executions and stronger
observability. One function run plus each step is billable as an execution.
GoTime deploys its functions on its own compute but needs no managed queue or
worker fleet in the hosted model.

The local development server is a single open-source process and works with
Docker Compose. Self-hosting is possible, but production-scale guidance moves
toward PostgreSQL, Redis, monitoring, and potentially Kubernetes, shifting the
same operational burden back to GoTime. Managed Inngest also creates stronger
event/step and hosted-service lock-in than keeping policy in plain services.

### Option E — `adopt_openai_agents_sdk`

#### What it solves

The Agents SDK provides an agent loop, tools/handoffs, input/output/tool
guardrails, approval interruptions, sessions, resumable serialized run state,
and built-in tracing. It can be constrained, and GoTime could expose only one
bounded tool without granting general autonomy.

#### What it does not solve

Official OpenAI documentation says the application/server owns deployment,
tool implementations, state storage, and approval decisions. Sessions are
conversation/run continuation, not a durable workflow event store. Serialized
approval state still needs application storage. The SDK supplies no durable
15-minute/7-day/24-hour scheduler, crash-recoverable state-machine service,
budget transaction, dispatch-consumption ledger, or general long-running
workflow runtime.

Its run loop normally continues through model calls, tools, and handoffs until
a stopping point. That abstraction is unnecessary for one predetermined
request with no model-selected sequencing. Direct Responses API usage is
simpler, easier to bind to the frozen request, and less likely to imply agent
autonomy. Agents SDK tracing could be valuable later, but traces are
observability, not GoTime's durable truth.

#### Cost

The official pricing material documents API model/tool usage rather than a
separate Agents SDK orchestration charge. The practical recurring cost is the
underlying API usage and any optional platform tools/tracing/storage. This is
cheap at GoTime's bounded volume, but it saves little control-plane engineering
and adds OpenAI-specific orchestration coupling.

**Answer:** adopting the Agents SDK would not solve the problem under review.
It mainly simplifies AI invocation and tool orchestration; the durability and
authorization control plane would remain ours.

### Option F — `selective_hybrid`

The credible hybrid is **GoTime policy plus Temporal durability**, not a mix of
multiple agent frameworks. GoTime's immutable package, cases, envelopes,
grants, budgets, dispatch rule, validators, fallback, evidence, and scoring
would remain ordinary policy modules. Temporal would own workflow history,
timers, external waits, replay, and worker recovery.

This is technically strong and likely the best future production architecture
if GoTime develops many long-running planning workflows. It loses now because
the migration and service burden arrives before demonstrated product demand,
and the immediate Milestone 5 budget engine remains almost entirely custom.
LangGraph or Inngest could be substituted in this pattern, but each removes
less exact generic plumbing or introduces a less natural execution model.

### Option G — `defer_adoption`

Continue Architecture A through the next policy-heavy milestones, keep the
current implementation explicitly experimental, and establish measurable
triggers for a generic-infrastructure decision:

- before product integration or relying on unattended 24-hour deadlines;
- before Milestone 13/14 becomes a production persistence commitment;
- when a second real bounded AI capability needs the same durable lifecycle;
- when planning features need durable multi-day waits/schedules beyond this
  evaluation;
- when custom recovery/timer code exceeds the cost of one managed service and
  worker model.

This option preserves learning and avoids premature lock-in. It does not mean
“never adopt”; it prevents the narrow formal evaluation from choosing the
product workflow platform by accident.

## 5. Cost analysis

Prices below are official list prices observed on **2026-08-11**. They exclude
GoTime's existing compute, provider token usage, taxes, support negotiation,
and engineering time unless noted.

| Candidate | Direct recurring vendor cost | Infrastructure cost | Engineering cost | Lock-in/migration cost |
|---|---|---|---|---|
| Custom | No new orchestration bill. | Current process/files are minimal; production requires a database, scheduler/worker, backup, monitoring, and security decision. | Highest remaining build and adversarial-hardening work. | Lowest framework lock-in; highest custom-schema migration work later. |
| LangGraph OSS | Free, MIT-licensed library. | Durable checkpointer/database, app process, scheduling, monitoring, backup, upgrades are self-managed. | Medium migration/learning; still substantial policy and side-effect work. | Medium: graph/checkpoint APIs and thread state; policy can stay portable if isolated. |
| LangSmith hosted | Developer `$0/seat` is observability-oriented; Plus is `$39/seat/month` plus usage and includes one small serverless deployment. LCU is `$1.50`; LSU is `$1.00`, with deployment resource metering. | Managed persistence/deployment reduces service operations. | Medium; platform setup and graph refactor. | Medium-high proprietary deployment/state coupling. |
| Temporal Cloud | Essentials starts at `$100/month`; includes 1M Actions, 1 GB active and 40 GB retained storage. Overage starts at `$50/million` Actions; active storage `$0.042/GBh`, retained `$0.00105/GBh`. | GoTime still runs workers; Temporal runs service/storage. | High initial migration and deterministic-workflow learning; large later savings in durability/timers. | Medium: Workflow/Activity APIs and Event History are Temporal-specific, though policy code can remain plain. |
| Temporal self-hosted | Open source; no Temporal license charge. | Highest: service, persistence/visibility stores, workers, monitoring, backup, security, schema/server upgrades. | Highest operational learning/support burden. | Lower vendor dependence, significant framework/state-history dependence. |
| Inngest Cloud | Hobby `$0/month`: 50k executions, five concurrent. Pro starts at `$99/month`: 1M+ executions, 100+ concurrent. Run plus each step is an execution. | App/functions remain on GoTime compute; queue/orchestration hosted. | Medium; event/step refactor and exact-policy adapters. | Medium-high event/step/platform coupling; 24-hour idempotency is insufficient alone. |
| Inngest self-hosted | Open-source core, no managed bill. | Default SQLite/in-memory Redis is simple; production can require Postgres, Redis, monitoring, and Kubernetes. | Medium-high operations and upgrades. | Medium framework/state coupling. |
| OpenAI Agents SDK | No separate SDK orchestration price documented; underlying model/tool API usage applies. | Existing app compute and GoTime-owned persistence remain. | Low integration effort, but almost no durability work disappears. | High provider-SDK orchestration coupling relative to its limited benefit here. |

### Scale interpretation

- **Friends/family:** custom has the lowest total cash cost and fewest moving
  parts. Inngest Hobby is financially viable but adds a hosted dependency.
  Temporal Cloud's `$100/month` minimum alone exceeds GoTime's stated
  `$25–$50/month` early operating target. LangSmith Plus and Inngest Pro also
  consume most or more than that target before model/hosting cost.
- **Early public beta:** managed Inngest becomes cost-attractive if GoTime has
  genuine background/scheduled workflows; Temporal becomes defensible if
  correctness and long waits are product-critical. Hosted LangGraph is more
  attractive only if graph-based AI workflows and LangSmith observability are
  also desired.
- **Moderate future scale:** engineering/on-call cost dominates. Temporal's
  maturity and durable semantics can outweigh its platform bill. Inngest can
  be simpler for event-driven product workflows. Custom remains viable only if
  GoTime deliberately invests in a general durable-execution subsystem.

“No vendor bill” is not free: custom engineering, failure testing, migrations,
monitoring, and recovery support are operating costs.

## 6. Operational-simplicity analysis

| Candidate | Moving parts at initial scale | Local development | Production deployment | Failure/debug transparency | Small-team assessment |
|---|---|---|---|---|---|
| Custom | Existing Python process and local state | Simplest; ordinary tests/files | Simple only while offline; production durability unresolved | Excellent at current scale because every event is visible | Best now, with an explicit stop before accidental productionization |
| LangGraph OSS | App plus checkpointer/database | Good, in-memory or local checkpointer | GoTime owns persistence, scheduling, monitoring, backup | Graph/checkpoint replay adds concepts | More abstraction without fully removing operations |
| LangSmith hosted | App plus hosted deployment/service | Good Agent Server/Studio experience | Managed, but Plus account/API/platform configuration | Strong traces/state UI; proprietary service failure modes | Reasonable, but agent platform exceeds current need |
| Temporal Cloud | Temporal service endpoint plus GoTime workers | Excellent single-binary dev server | Workers, namespace/config, deployment/versioning; service managed | Excellent Event History/Web UI; replay debugging has learning curve | Technically excellent, operationally disproportionate now |
| Temporal self-hosted | Multiple server services, DB, visibility, workers, UI | Easy dev server, unlike production | Heaviest candidate | Mature observability but broad on-call surface | Poor fit for one developer/friends-and-family |
| Inngest Cloud | App endpoint or Connect worker plus hosted platform | Excellent single dev server, Compose-friendly | Simple managed orchestration; app must be reachable or connected | Strong run/step traces; event races/idempotency windows need care | Best hosted operational fit, but not the best semantic fit |
| OpenAI Agents SDK | Existing app only | Simple SDK | Existing app deployment, persistence still ours | Good model/tool traces; no workflow crash history | Simple addition that does not simplify the target problem |

The framework-avoidance questions produce the following answers:

- **Could we maintain the immediate generic functionality ourselves?** Yes,
  for the bounded offline evaluation and Milestone 5. The answer becomes less
  certain for unattended deadlines and multiple production capabilities.
- **Would a framework reduce total complexity now?** Temporal would replace
  plumbing but add greater deployment/migration complexity. LangGraph and the
  Agents SDK mostly move or wrap complexity. Inngest reduces operations but
  adds event/platform semantics around rules GoTime must still own.
- **Would most custom lifecycle logic remain?** Policy lifecycle logic remains
  with every candidate; only persistence, timers, waits, and replay disappear.
- **Does a framework solve a broader future problem?** Temporal and Inngest
  plausibly do if multi-topic plans need durable reminders, human waits, and
  long-running workflows. That need is not yet demonstrated in the product.

## 7. Remaining Milestones 5–18 impact matrix

Legend:

- **G** — still fully GoTime-specific.
- **P** — policy remains GoTime-owned; generic mechanics materially simplify.
- **R** — generic implementation is largely replaced by the framework.
- **H** — adoption makes this milestone harder or broadens its infrastructure.

“Custom” means continue Architecture A. “Agents” means using the Agents SDK as
the primary new abstraction, not merely an optional invocation library.

| Milestone | Custom | LangGraph | Temporal | Inngest | Agents | Specific effect |
|---|---:|---:|---:|---:|---:|---|
| 5 Prospective budgets | G | G | P | P | G | Ceiling, reservation, reconciliation, and concurrency rules remain ours; durable runtimes can host atomic state transitions but do not define them. |
| 6 Dispatch consumption | G | P | P | P | H | Framework node/activity/step can isolate dispatch, but exact consumption-before-call and uncertainty remain ours. Agents' tool loop obscures rather than improves the seam. |
| 7 Generation grants | G | G | P | P | G | Exact preflight evidence, identity, and generation policy remain ours; persistence can simplify lifecycle storage. |
| 8 Same-shell boundary | G | H | H | H | H | Credential inheritance and direct human launcher remain GoTime security policy; hosted runtimes add another process/network boundary. |
| 9 Validation and closure | G | P | P | P | P | Validators/fallback/classification remain ours; durable completion/closure mechanics simplify. |
| 10 Human review/deletion/deadline | G | P | R | R | P | Temporal/Inngest strongly reduce durable wait/timer/restart work; evidence and terminal/deletion policy remain ours. |
| 11 Hard-gate acknowledgement | G | P | P | P | P | Exact acknowledgement semantics remain ours; interruption/signal/event storage simplifies. |
| 12 Aggregate extension | G | P | P | P | G | Extension policy remains ours; timer/history persistence simplifies. Agents has no durable aggregate timer. |
| 13 Pause/resume | G | R | R | R | P | This is a core LangGraph/Temporal/Inngest capability. Agents can serialize run state but leaves durable storage/scheduling ours. |
| 14 Aggregate history model | G | R | R | R | G | Framework history/checkpoints replace much plumbing, but GoTime still needs semantic audit/provenance and exportable final proof. |
| 15 Operator commands | G | P | P | P | H | Commands become clients/adapters to framework workflows; another operational surface must be secured and rehearsed. |
| 16 Exact-command rehearsal | G | G | G | G | G | Exact workflow and safety evidence remain GoTime-specific. |
| 17 Architecture proof | G | G | G | G | G | Guarantees cannot be delegated to framework feature claims. |
| 18 Live-readiness package | G | G/H | G/H | G/H | H | Identity, credentials, authority, and human review remain ours; hosted services add deployment/data/security review. |

### Real implementation savings

If Temporal were adopted, these concepts would largely disappear or shrink:

- custom journal append/storage and current projection reconstruction;
- explicit history-first two-file crash recovery;
- process-restart replay plumbing;
- grant/aggregate/review timers and scheduler recovery;
- generic pause/resume, wait-for-human, and extension persistence;
- much of worker retry/recovery and operational run visibility.

LangGraph removes checkpoint/replay/interrupt plumbing but still requires a
production checkpointer and, without hosted LangSmith, scheduling/operations.
Inngest removes queue, checkpoint, wait, and scheduling infrastructure while
retaining more event-correlation logic. Agents SDK removes almost none of this.

No candidate removes deterministic eligibility, frozen envelopes, grant
identity, prospective budgets, dispatch consumption, validators, fallback,
scoring, evidence review/deletion policy, or case closure.

## 8. Existing Milestones 1–4 reuse analysis

| Existing work | Stay/defer | LangGraph | Temporal | Inngest | Agents SDK |
|---|---|---|---|---|---|
| Immutable aggregate/package models | Directly reusable | Reusable as graph state/policy | Reusable as Workflow inputs/policy | Reusable as event/state policy | Reusable outside agent run |
| M1 JSON journal/projection/recovery | Directly reusable in experimental scope | Replaceable generic plumbing | Replaceable generic plumbing | Replaceable generic plumbing | Still required |
| M1 operation semantics and adversarial tests | Directly reusable | Reusable specification/tests | Reusable specification/tests | Reusable specification/tests | Still required |
| M2 deterministic bypass | Directly reusable | Directly reusable node/service | Directly reusable Workflow policy | Directly reusable step/service | Keep outside model loop |
| M3 envelope schema/digests | Directly reusable | Directly reusable state values | Directly reusable inputs/search attributes or payloads | Directly reusable event/state payloads | Keep outside agent loop |
| M3 substitution tests | Directly reusable | Retain unchanged at policy boundary | Retain unchanged at policy boundary | Retain unchanged at policy boundary | Retain unchanged |
| M4 grant schema/digest/budget port | Directly reusable | Reusable policy; replace event storage | Reusable policy; replace event storage | Reusable policy; replace event storage | Still needs GoTime persistence |
| Local file locking/fsync/fault injection | Directly reusable offline | Likely retired after migration | Likely retired after migration | Likely retired after migration | Still required |

Milestones 1–4 are not wasted work under this decision. They remain working
GoTime policy, executable specifications, adversarial tests, migration
acceptance criteria, and framework-neutral identity definitions. If generic
persistence is replaced later, the hash-chained journal/projection plumbing may
be retired, but its invariants and tests remain the acceptance specification
and reference oracle.

Tests that must survive any migration include:

- deterministic 07/08 provider bypass and constructor non-entry;
- exact aggregate, case, case-input, request, attempt, and provider identity;
- cross-case substitution and envelope uniqueness/order;
- exact grant/envelope/phase/lifetime binding;
- inclusive aggregate/grant/review expiration policy;
- zero retries and one-attempt non-reuse;
- per-case/aggregate prospective budget boundaries;
- consumption immediately before provider dispatch and conservative uncertain
  dispatch handling;
- acknowledgement, review/deletion, terminal closure, and immutable final
  provenance;
- crash/restart tests at every durable boundary.

## 9. Scoring methodology

Each criterion is scored 1–5, where 5 is best for GoTime. For burden, cost,
infrastructure, and lock-in, 5 means **lower** burden/cost/lock-in. The weighted
score is `sum(score × weight) / sum(weights)`; maximum is 5. Scores reflect the
current friends/family phase, not an enterprise platform in isolation.

Weights deliberately favor deterministic control, exact capability boundaries,
dispatch safety, implementation savings, maintenance, operational simplicity,
and total cost over feature breadth.

| Criterion | Weight | Stay custom | LangGraph | Temporal | Inngest | Agents SDK | Selective hybrid | Defer adoption |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Deterministic-core fit | 8 | 5 | 4 | 5 | 4 | 3 | 5 | 5 |
| Bounded-capability fit | 7 | 5 | 4 | 5 | 4 | 4 | 5 | 5 |
| Exact case-identity fit | 7 | 5 | 4 | 5 | 4 | 3 | 5 | 5 |
| Durability/recovery | 5 | 3 | 4 | 5 | 5 | 2 | 5 | 3 |
| Timers/expiration | 3 | 2 | 2 | 5 | 5 | 1 | 5 | 2 |
| Pause/resume | 4 | 3 | 5 | 5 | 5 | 3 | 5 | 3 |
| Human-review waits | 4 | 2 | 5 | 5 | 5 | 4 | 5 | 2 |
| Zero-retry control | 5 | 5 | 4 | 5 | 5 | 3 | 5 | 5 |
| Exact dispatch-boundary fit | 7 | 5 | 3 | 5 | 2 | 2 | 5 | 5 |
| Provider-uncertainty handling | 5 | 4 | 3 | 5 | 3 | 2 | 5 | 4 |
| Implementation effort saved | 7 | 1 | 4 | 5 | 4 | 2 | 4 | 2 |
| Low maintenance burden | 7 | 2 | 3 | 3 | 4 | 3 | 3 | 3 |
| Operational simplicity | 8 | 5 | 3 | 2 | 4 | 4 | 2 | 5 |
| Local development | 4 | 5 | 4 | 4 | 5 | 4 | 4 | 5 |
| Deployment simplicity | 6 | 5 | 3 | 2 | 4 | 4 | 2 | 5 |
| Debugging transparency | 5 | 5 | 3 | 4 | 3 | 4 | 4 | 5 |
| Observability | 3 | 2 | 4 | 5 | 5 | 5 | 5 | 2 |
| Low direct recurring cost | 6 | 5 | 4 | 2 | 3 | 5 | 2 | 5 |
| Low infrastructure cost | 6 | 5 | 3 | 2 | 4 | 5 | 2 | 5 |
| Low lock-in | 5 | 5 | 3 | 3 | 2 | 2 | 3 | 5 |
| Maturity | 3 | 3 | 4 | 5 | 4 | 4 | 5 | 4 |
| Initial GoTime-scale fit | 8 | 5 | 3 | 2 | 3 | 3 | 2 | 5 |
| Future multi-topic fit | 4 | 3 | 4 | 5 | 4 | 3 | 5 | 4 |

Total weight: 127.

## 10. Scored comparison

| Rank | Decision option | Weighted score / 5 | Score / 100 | Interpretation |
|---:|---|---:|---:|---|
| 1 | `defer_adoption` | 4.25 | 85.0 | Best current-scale decision; preserves migration choice. |
| 2 | `stay_custom` | 4.09 | 81.7 | Best immediate architecture, but risks accidental long-term commitment. |
| 3 | `adopt_temporal` | 3.94 | 78.7 | Best technical durability; cost/operations are premature. |
| 4 | `selective_hybrid` | 3.88 | 77.6 | Best plausible future shape; migration timing is wrong now. |
| 5 | `adopt_inngest` | 3.84 | 76.9 | Best hosted simplicity; weaker exact-dispatch/idempotency fit. |
| 6 | `adopt_langgraph` | 3.57 | 71.3 | Good checkpoints/HITL, incomplete generic platform unless hosted. |
| 7 | `adopt_openai_agents_sdk` | 3.25 | 65.0 | Useful invocation SDK, not a durability solution. |

Scores are decision aids, not claims of general product quality. Temporal's
lower operational-simplicity score is specific to GoTime today; at moderate
scale its total score would rise materially.

## 11. Approved decision record

### Decision: `defer_adoption`

**Implementation consequence:** continue the custom Architecture A control
plane through Milestones 5–9.

**Immediate next step:** Milestone 5 — prospective budgets, after this decision
record is reviewed and committed.

**Framework PoC:** not required before Milestone 5.

**Required reassessment:** after committed Milestone 9 and before Milestone 10.

**Reassessment scope:** primarily Temporal, Inngest, and LangGraph for generic
durable-execution infrastructure.

**OpenAI Agents SDK:** not adopted for this control-plane problem.

Milestones 5–9 complete the core GoTime-specific provider transaction:

`budget → dispatch consumption → generation authority → credential/provider
boundary → result validation and closure`

Those milestones remain under direct GoTime control:

5. prospective budgets;
6. dispatch consumption;
7. generation grants;
8. the same-shell boundary; and
9. result validation and closure.

Keep the Milestone 5 budget engine behind the Milestone 4 fail-closed port and
under the current aggregate lock. Do not refactor journals or introduce
framework types inside frozen package/envelope/grant identities.

Top reasons:

1. Milestone 5 is a safety-policy transaction, not primarily a workflow-runtime
   problem. A framework would host but not eliminate it.
2. The present workload is bounded, local, operator-driven, and extremely low
   volume. New services and framework semantics cost more than they save now.
3. The committed policy objects and adversarial tests provide a clean migration
   contract. Waiting for a real product-level timer/wait/multi-capability need
   improves the architecture decision without weakening evaluation integrity.

What must remain GoTime-owned regardless of any future runtime: deterministic
eligibility; bounded capability definitions; curated grounding; frozen case
and request identities; AI case envelopes; grants and exact authorization
semantics; prospective budget and zero-retry policy; exact one-attempt
semantics; the `provider_dispatch_started` consumption rule; uncertain-dispatch
handling; validators and deterministic fallback; result acceptance and
evidence semantics; evaluation/scoring rules; hard-gate continuation policy;
and closure semantics.

What should be most strongly considered for later replacement: durable history
storage, replay/projection, crash recovery, timers, waits, scheduling, and
worker recovery. Temporal is the strongest technical candidate for that layer;
Inngest is the strongest operationally simple hosted candidate if GoTime's
future workflows are predominantly event-driven reminders and approvals.

### Mandatory checkpoint before Milestone 10

After Milestone 9 is committed and before Milestone 10 begins, reassess whether
generic durable-execution infrastructure should remain custom. Milestones
10–14 shift toward human review/deletion deadlines, hard-gate acknowledgement,
aggregate extension, pause/resume, and the aggregate history model. The review
must compare Temporal, Inngest, and LangGraph specifically for:

- timers and scheduling;
- durable human waits and pause/resume;
- long-running workflow state and recovery;
- history/checkpoint persistence and operational tracing;
- total custom code accumulated and its maintenance burden;
- operational burden;
- migration cost and then-current product scale.

This checkpoint is a deliberate reassessment, not a predetermined migration.
Do not automatically adopt a framework at Milestone 10.

### OpenAI Agents SDK disposition

The OpenAI Agents SDK is not recommended for this control-plane problem now.
It may help with model/tool orchestration, guardrails, tracing, and related AI
interaction mechanics, but it does not materially replace the durable workflow
infrastructure being considered. Direct, bounded model-call control remains the
better fit. Reconsider the SDK separately only if model/tool orchestration
becomes complex enough to justify it.

### Future framework dispositions

- Temporal remains the strongest candidate for heavy-duty durability and
  recovery.
- Inngest remains a strong candidate for simpler hosted workflow execution.
- LangGraph remains relevant for checkpointed state and human-in-the-loop
  orchestration.
- None justifies migration before Milestone 5.

## 12. Runner-up

### `stay_custom`

It wins on control, current simplicity, cost, and transparency. It loses to
`defer_adoption` because “stay custom” can become an unexamined permanent
choice. GoTime should not finish Milestones 13–14 and silently treat local JSON
replay as production architecture without reconsidering durable infrastructure.

Temporal is the runner-up technology, even though `stay_custom` is the runner-up
decision. If a framework must be selected later, Temporal best matches exact
history, timers, human waits, long execution, and crash recovery.

## 13. Minimal proof of concept

### Recommendation now

**No infrastructure PoC should block Milestone 5.** It would delay a
GoTime-specific budget decision while testing features not required to complete
that milestone.

### Triggered future PoC

Before production integration, unattended Milestone 10 deadlines, or treating
Milestones 13–14 as product infrastructure, run a time-boxed **Temporal Cloud
or local Temporal versus current custom** PoC. Do not port the formal
evaluation. Use:

- one synthetic aggregate and one immutable case identity;
- one existing-format AI envelope and preflight grant candidate;
- one exact 15-minute durable timer;
- one external pause, runtime/worker restart, and resume;
- zero Activity retries (`maximum_attempts=1`);
- one synthetic single-use authority and durable consumed-before-activity
  marker;
- no credential, provider client, network provider request, or live cost.

Pass criteria:

1. Identity/envelope/grant values are byte/canonically unchanged.
2. Restart before and after the consumption marker has one unambiguous,
   conservative outcome and never produces a second attempt.
3. The timer expires at the exact inclusive boundary without a running worker.
4. Human pause/resume survives service/worker restart.
5. A fully replayed history yields the same policy projection as the custom
   reference and passes retained adversarial identity/expiry tests.
6. The PoC removes at least the custom journal/projection/crash/timer code it
   claims to replace; it does not duplicate it behind Temporal.
7. Local setup, deployment, and diagnosis are acceptable to one developer, and
   estimated recurring cost fits the then-current GoTime budget.

Fail if any frozen identity changes, a provider attempt can repeat, policy moves
into opaque framework configuration, custom persistence remains duplicated, or
operations exceed the demonstrated product value.

## 14. Migration implications

If a later Temporal hybrid passes the PoC:

- likely retire or narrow the storage/replay portions of
  `v4_formal_evaluation_live_state.py` and future custom timer/scheduler code;
- keep `v4_formal_evaluation_live_models.py`, deterministic eligibility,
  `v4_formal_evaluation_live_cases.py`, grant identity/budget policy,
  validators, fallback, evidence policy, and scoring;
- retain all semantic/adversarial tests and add Temporal replay/history tests;
- translate current operations into Workflow decisions and Activities without
  using Event History as the only human-readable proof artifact;
- keep package, envelope, and grant identities unchanged because persistence
  implementation is not part of those immutable contents;
- give the new workflow runtime/state schema its own version rather than
  rewriting committed local history.

No frozen formal-evaluation identity should need to change merely because the
storage engine changes. If a proposed migration changes canonical package,
envelope, request, attempt, or grant semantics, it creates evaluation-integrity
risk and must stop. Migration before Milestone 5 is not recommended; a later
migration should begin from a closed synthetic aggregate and compare both
implementations against the same policy oracle.

## 15. Risks and uncertainties

- The largest uncertainty is whether GoTime will soon need durable product
  workflows across many planning topics. If it does, waiting too long raises
  migration cost; if it does not, adopting now is pure overhead.
- Milestone 10's unattended 24-hour deadline is the first requirement likely to
  expose the limits of invocation-driven local expiration. It must not be
  claimed live-ready without a reviewed scheduler/runtime.
- Temporal's Activity at-least-once semantics demand a PoC of the exact
  dispatch-consumption/uncertain-result rule; “durable execution” is not proof
  of exactly-once provider behavior.
- Inngest's managed simplicity is appealing, but free-tier limits, 24-hour
  idempotency semantics, hosted retention, and paid-plan pricing can change.
- LangGraph and OpenAI Agents SDK product surfaces evolve quickly. Adoption
  could increase upgrade churn around a stable, deliberately simple capability.
- Hosted services improve access control, managed persistence, auditability,
  and backups, but also introduce service credentials, external data handling,
  availability dependencies, and another security review. Current
  friends/family scope does not justify premature GA controls.
- The current unkeyed local hash chain remains tamper-evident only relative to
  its retained head; none of this review upgrades that threat model.

## 16. Accepted decision and Milestone 5 boundary

The human decision is `defer_adoption`. Milestone 5 may begin on the existing
committed Architecture A implementation after this documentation change is
reviewed and committed.

Milestone 5 should **not** remain paused for a framework PoC, and the remaining
plan does **not** need revision before Milestone 5. Architecture A proceeds
through Milestone 9. A mandatory architecture reassessment follows committed
Milestone 9 and precedes Milestone 10. Until this decision record is reviewed
and committed, Milestone 5 remains paused and all committed Architecture A code
remains untouched.

## 17. Sources consulted

All product claims and prices were checked against official primary sources on
**2026-08-11**. Prices and service packaging are time-sensitive.

### GoTime repository

- `README.md`, `docs/product-vision.md`, `docs/cost-and-operations.md` — product,
  deterministic-core, operational, and cost principles.
- `docs/adr/ADR-0004-single-shell-live-credential-boundary.md` — operator and
  credential process boundary.
- `docs/adr/ADR-0005-authenticated-offline-evaluation-history.md` — journal,
  replay, deletion recovery, and explicit non-production-persistence scope.
- `docs/experiments/suggest-moving-service-questions/v4-formal-evaluation-live-implementation-plan.md`
  — remaining Milestones 5–18.
- Committed Milestone 1–4 implementation, tests, and milestone notes — actual
  operation grammar, persistence, deterministic bypass, envelopes, and grants.

### LangGraph and LangSmith

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
  — low-level runtime, durable execution, and human-in-the-loop.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
  — checkpoints, threads, pending writes, time travel, and recovery.
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
  — persisted pause/resume and idempotent side-effect guidance.
- [LangGraph fault tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance)
  — opt-in retry policies, timeouts, and error handling.
- [LangSmith FAQ](https://docs.langchain.com/langsmith/faq) — open-source versus
  hosted persistence, scheduling, monitoring, deployment, and licensing.
- [LangSmith pricing](https://www.langchain.com/pricing) — plans, LCU/LSU,
  deployment, resource metering, and trace retention.
- [LangSmith platform setup](https://docs.langchain.com/langsmith/platform-setup)
  — cloud, hybrid, self-hosted, and local Agent Server options.

### Temporal

- [Temporal Workflows](https://docs.temporal.io/workflows) — Event History as
  source of truth, deterministic replay, recovery, and Activity boundary.
- [Temporal Activities](https://docs.temporal.io/activities) — external work,
  worker execution, results, and idempotency recommendation.
- [Temporal Python error handling](https://docs.temporal.io/develop/python/best-practices/error-handling)
  — Activity at-least-once behavior, retry defaults, and `maximum_attempts`.
- [Temporal durable timers](https://docs.temporal.io/develop/python/workflows/timers)
  — persisted timers across worker/service downtime.
- [Temporal Workflow message passing](https://docs.temporal.io/develop/python/workflows/message-passing)
  — Queries, Signals, Updates, and wait conditions.
- [Temporal self-host guide](https://docs.temporal.io/self-hosted-guide) and
  [deployment guide](https://docs.temporal.io/self-hosted-guide/deployment) —
  local dev server, production operations, PostgreSQL/Elasticsearch example,
  monitoring, security, visibility, and upgrades.
- [Temporal Cloud pricing](https://docs.temporal.io/cloud/pricing) and
  [plan page](https://temporal.io/pricing) — plan minimums, Actions, and storage.

### Inngest

- [Inngest steps](https://www.inngest.com/docs/learn/inngest-steps) and
  [execution model](https://www.inngest.com/docs/learn/how-functions-are-executed)
  — checkpointed steps, persisted results, and resume.
- [Retries and error handling](https://www.inngest.com/docs/guides/error-handling)
  — four default retries and `retries: 0`.
- [Wait for event](https://www.inngest.com/docs/features/inngest-functions/steps-workflows/wait-for-event)
  and [human-in-the-loop](https://www.inngest.com/docs/ai-patterns/human-in-the-loop)
  — external waits, timeouts, and approvals.
- [Idempotency](https://www.inngest.com/docs/guides/handling-idempotency) — event
  and function idempotency behavior and 24-hour period.
- [Local development](https://www.inngest.com/docs/local-development),
  [deployment](https://www.inngest.com/docs/platform/deployment), and
  [self-hosting](https://www.inngest.com/docs/self-hosting) — dev server,
  hosted invocation, SQLite/Redis defaults, and production infrastructure.
- [Inngest pricing](https://www.inngest.com/pricing) — Hobby/Pro tiers,
  concurrency, execution units, and observability.
- [Inngest usage limits](https://www.inngest.com/docs/usage-limits/inngest) —
  retention, run length, sleep, and state limits.

### OpenAI Agents SDK

- [Agents SDK overview](https://developers.openai.com/api/docs/guides/agents) —
  SDK scope and application ownership of deployment, storage, and approvals.
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
  — agent loop, sessions, conversation state, and continuation strategies.
- [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
  — tool approval interruptions and serialized resumable state.
- [Results and state](https://developers.openai.com/api/docs/guides/agents/results)
  — SDK result and run-state surfaces.
- [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
  — built-in tracing and runtime-owned connectivity/approval boundaries.
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing) — model
  and tool/API usage pricing; no separate durable-workflow service is provided
  by the Agents SDK.
