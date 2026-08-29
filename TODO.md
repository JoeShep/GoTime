# TODO

## Domain language

- [ ] Define GoTime's core domain objects: Goal, Project, Task, Milestone,
  and Dependency.
- [ ] Document the relationships and boundaries between those concepts before
  designing persistence.

## Derived attention

- [x] Manually walk through the home-sale strategy reference scenario and
  identify the smallest representation needed to recommend gathering realtor
  evidence, prepare the strategy Decision, activate conditional work, and
  coordinate it toward the **Start selling our home** Milestone.
- [x] Audit the current implementation and prepare an implementation-neutral
  technical design for the smallest vertical slice.
- [x] Review and approve the technical design and Increment 1 architecture.
- [x] Implement and verify Increment 1: the Milestone and Decision foundation
  on test databases and an isolated restored volume.
- [x] Complete human acceptance of Increment 1, deploy the accepted frontend
  to the normal stack, and remove the isolated acceptance environment safely.
- [x] Approve and implement the first Increment 2 slice: one-level required
  subtasks, derived/manual parent status, dependency propagation, and isolated
  migration rehearsal.
- [x] Complete human acceptance, additive active migration, normal deployment,
  database verification, and isolated teardown for the required-subtask slice.
- [x] Implement the isolated Increment 2 preparation relationship and advisory
  Decision-readiness candidate without changing Recommendations or family data.
- [x] Complete human acceptance, additive active migration, normal deployment,
  database verification, and isolated teardown for Decision preparation readiness.
- [x] Design and implement the isolated contextual Recommendation candidate for
  Decision preparation with structured deterministic signals and no new schema.
- [x] Complete human acceptance, complete suites, deployment, and closeout for
  contextual Decision-preparation Recommendations.
- [x] Review, approve, rehearse, deploy, and close the first family
  Milestone/Decision conversion.
- [ ] Define and validate the working Do now, Coming soon, Later, and Waiting
  states as deterministic outputs rather than user-selected priorities.
- [x] Calibrate the focused deterministic Recommendation ranking baseline:
  viewer-local holds, due-pressure propagation, bounded attention signals, and
  transitional priority as the weakest meaningful fallback.
- [ ] Specify which existing plan facts contribute to each state without
  changing the stored priority field or existing data.
- [ ] Test a no-AI baseline against representative tasks in the real family
  plan and record which missing facts prevent trustworthy recommendations.
- [ ] Define a structured planning-knowledge contract only after the baseline
  demonstrates which additional facts are necessary.

## Now, Plan, and Experiments

- [x] Audit the current rendered interface and approve the Now/Plan navigation
  and default-off Experiments boundary.
- [x] Select an established routing dependency and record the architecture in
  an ADR.
- [x] Prepare the first structural implementation increment: extract and gate
  Experiments without beginning derived-attention Increment 2.
- [x] Complete isolated human acceptance of the first routing and Experiments
  boundary increment, deploy it to the normal stack, and remove the disposable
  acceptance environment safely.
- [x] Introduce the initial Now/Plan shell, separate persisted Recommendation
  and Plan content, and default-off the suspended Experiments boundary.
- [x] Implement, accept, and deploy collapsible phases with browser-session
  phase/completed-section expansion state; remove the disposable acceptance
  environment safely.
- [x] Complete human acceptance, deployment, and closeout of the shared
  cross-route Find panel and browser-session Plan scroll restoration candidate.
- [x] Complete human acceptance, deployment, and closeout of the implemented
  cross-route Recommendation reveal candidate.
- [x] Complete human acceptance, deployment, and closeout of the implemented
  persistent mobile Now, Plan, and Find bottom navigation candidate.
- [x] Complete human acceptance, deployment, and closeout of the implemented
  unified Task, Milestone, and Decision Plan Add menu candidate, including its
  final prospective plan-wide duplicate-title validation extension.

## Milestone-driven planning questions

- [ ] Determine how Decision evidence and confidence need to be represented.
- [x] Determine the minimum behavior for activating work conditionally from a
  selected Decision option while preserving inactive branches.
- [ ] Determine how revisable Decisions retain previous outcomes and rationale.
- [ ] Determine how private constraints can participate in reasoning without
  unnecessary disclosure.
- [ ] Determine how approximate Milestone windows become more precise and how
  range-based financial estimates avoid false precision.
- [ ] Decide whether an Evidence need must be a first-class domain concept or
  can initially use ordinary Tasks and notes.
