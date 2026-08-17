# TODO

## Domain language

- [ ] Define GoTime's core domain objects: Goal, Project, Task, Milestone,
  and Dependency.
- [ ] Document the relationships and boundaries between those concepts before
  designing persistence.

## Derived attention

- [ ] Define and validate the working Do now, Coming soon, Later, and Waiting
  states as deterministic outputs rather than user-selected priorities.
- [ ] Specify which existing plan facts contribute to each state without
  changing the stored priority field or existing data.
- [ ] Test a no-AI baseline against representative tasks in the real family
  plan and record which missing facts prevent trustworthy recommendations.
- [ ] Define a structured planning-knowledge contract only after the baseline
  demonstrates which additional facts are necessary.
