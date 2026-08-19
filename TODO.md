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
- [ ] Review and approve execution planning for Increment 2: required
  subtasks, work-informs-Decision relationships, advisory Decision readiness,
  and contextual Recommendations.
- [ ] Define and validate the working Do now, Coming soon, Later, and Waiting
  states as deterministic outputs rather than user-selected priorities.
- [ ] Specify which existing plan facts contribute to each state without
  changing the stored priority field or existing data.
- [ ] Test a no-AI baseline against representative tasks in the real family
  plan and record which missing facts prevent trustworthy recommendations.
- [ ] Define a structured planning-knowledge contract only after the baseline
  demonstrates which additional facts are necessary.

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
