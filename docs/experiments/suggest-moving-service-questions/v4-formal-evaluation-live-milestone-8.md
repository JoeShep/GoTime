# Architecture A Milestone 8 — same-shell provider boundary

## Status and scope

Milestone 8 is an offline, synthetic rehearsal of the operator/provider
boundary. No live authorization, real credential, provider request, generation
dispatch, or Milestone 9 result handling exists. The partial implementation at
continuation contained only a production-closed internal boundary; this
milestone completes its fixed launchers, validation order, and tests.

## Fixed launchers and credential lifecycle

The human directly runs
`run_v4_formal_evaluation_live_preflight_operator.zsh`. It accepts no case,
provider, model, request, grant, reservation, amount, or credential argument.
The coordination CLI remains its existing ten commands. A separate fixed
generation launcher exists, but intentionally performs only the credential-free
generation readiness check and fails before prompting while reviewed production
preflight evidence and Milestone 18 live authorization are absent.

The preflight launcher uses zsh, disables xtrace, performs the fixed readiness
check, then silently reads and exports
`GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY` into the single controlled child
process tree. EXIT/INT/TERM/HUP traps unset it and preserve the child status;
signal exits are 130/143/129. The secret is never accepted in argv or a file and
is excluded from journal, projection, logs, exceptions, and result handoff.
Both fixed launchers reject zsh `source` execution before changing options,
installing traps, prompting, exporting, or starting a child. Tests invoke the
unchanged preflight launcher with xtrace enabled and traverse its unchanged
Docker wrapper. A test-only `docker` process shim records the literal fixed argv
and runs the wrapper-selected entry module with a test-only import hook below
that boundary; neither public script is copied or rewritten. Docker argv
contains the credential variable name but never its value. Temporary files,
captured output, process arguments, journal, and projection are scanned for the
synthetic credential after success, failure, and signals.

## Ordering and provider isolation

The internal boundary derives the current case from replay-validated state,
binds the exact envelope/grant/reservation/request identities, checks the
aggregate/grant windows and zero retries, and constructs the local client before
final post-secret validation. It then completes the history-first,
projection-reconciled `provider_dispatch_started` transaction and immediately
enters the provider seam in the same child call stack. There is no human input,
second command, wait, or approval between durable return and entry.

The frozen OpenAI SDK is `openai==2.45.0`. Its default retry count is two, so
the execution boundary calls the canonical credential/client factory directly.
Constructor-observation tests exercise that path and prove `max_retries=0`,
`trust_env=False`, the fixed OpenAI base URL, no construction-time provider
operation, and one provider-entry attempt after a synthetic timeout/error.
For the frozen formal-evaluation execution environment, `trust_env=False` is
intentional: the HTTP client does not inherit ambient `HTTP_PROXY`,
`HTTPS_PROXY`, `ALL_PROXY`, or other environment-derived HTTP transport
configuration governed by httpx `trust_env` behavior. The provider boundary
therefore uses its explicitly constructed, reviewed transport configuration
instead of silently changing the request path based on the operator shell or
container environment. This statement is limited to environment-derived HTTP
client configuration; it does not claim to disable all operating-system or
network routing behavior. Milestone 8 validation remains network-disabled, no
live provider request occurred, and this client setting grants no provider
authority: live execution remains blocked by the existing authorization gates.
Frozen request configuration supplies the 5-second token-preflight and
12-second generation timeouts and fixes workflow/application automatic retries
at zero. Timeout never authorizes retry.

Production readiness is hard-false until Milestone 18 supplies a separately
reviewed live package. Production generation additionally fails on its absent
Milestone 9 reviewed-evidence prerequisite before any credential prompt.
Synthetic authorization, client, and SDK-entry behavior exist only in test
subclasses and cannot be selected by CLI, environment, configuration, or an
operator argument. The fixed container wrapper is network-disabled in this
milestone, so the real provider-operation count is zero.

Local/client or pre-dispatch persistence failure leaves the attempt reserved
and makes zero SDK entries. Once durable dispatch succeeds, a synthetic timeout
or provider error leaves the attempt consumed, unreleasable, and non-retryable.
The returned synthetic payload/error is only an interface to the future
Milestone 9 handler and is never persisted as trusted state.

Final revalidation tests isolate the mutable conditions rather than accepting
a masked failure: an aggregate prepared ten minutes before its seven-day
boundary crosses only that boundary while its new 15-minute grant remains
valid; separate cases cross only grant expiry, present a specifically released
reservation, or consume the reservation concurrently. Each reaches its exact
diagnostic before a second dispatch or provider entry.

Build-vs-adopt remains `defer_adoption`; Architecture A remains custom through
Milestone 9. Reassessment remains mandatory after committed Milestone 9 and
before Milestone 10.

The Milestone 7 full-offline result used the same test path in the pinned image
without zsh and therefore skipped 18 existing shell tests: four sequence-3
same-shell cases, four sequence-4 same-shell cases, four unittest-backed zsh
cases, four unittest-backed same-shell cases, one sequence-2 Docker rehearsal,
and one sequence-4 Docker/zsh rehearsal. Milestone 8 mounted the existing host
zsh read-only into the same network-disabled image. That enabled the sixteen
zsh-only cases; the two Docker-daemon-dependent rehearsals remain skipped. No
path or marker was removed, so the 18-to-2 change increases rather than narrows
coverage. The corrected apples-to-apples run uses the same command/image with
only the read-only zsh mount added.

Validation passed with 20 focused Milestone 8 tests, 222 focused Milestones
1–8 tests, and 1,254 full-offline tests with the two documented skips.
Backend passed 148,
frontend passed 17, and TypeScript/build, Python/JSON/TOML parsing,
frozen-foundation verification, shell syntax, and scoped diff checks passed.
The existing host zsh binary was mounted read-only into the pinned
network-disabled image for exact launcher/signal rehearsal; nothing was
installed and repository permissions were unchanged.
