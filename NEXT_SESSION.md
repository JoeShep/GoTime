# NEXT_SESSION

## Current objective: manually reason through the home-sale scenario

Use the
[home-sale strategy reference scenario](docs/reference-scenarios/home-sale-strategy.md)
to determine the smallest representation GoTime needs to derive and explain
this sequence:

1. Reengage with the realtor.
2. Gather enough market evidence to compare credible sale strategies.
3. Select the initial home-sale strategy.
4. Activate only the work required by the selected strategy.
5. Coordinate that work toward the post-New Year sale-launch Milestone.

This is a product-design exercise. Stop after the minimal representation and
reasoning walkthrough are reviewed. Do not propose or implement database,
Pydantic schema, API, interface, or persisted family-plan changes yet.

## What the walkthrough must establish

* Which current facts are sufficient to make `Reengage with the realtor` a Do
  now action without manual task priority or an arbitrary start date.
* How the unresolved strategy Decision and its credible options control which
  downstream work is relevant.
* Which relationships are universal hard prerequisites, route-specific
  conditional work, or supporting/timed work.
* How the minimum-net-proceeds hard constraint differs from the preferences
  used to compare viable options.
* What evidence and confidence are sufficient for a responsible Decision
  without demanding unavailable certainty or creating false precision.
* Which facts are missing from the current plan and therefore require an
  explicit representation or later planning knowledge.

The working derived attention states remain Do now, Coming soon, Later, and
Waiting. Their names and exact rules are provisional. Preserve the stored
Critical/High/Medium/Low priority field and all existing values until a
replacement has been designed and validated.

## Product sequence after the walkthrough

1. Define derived attention states and deterministic inputs.
2. Test the no-AI baseline against representative tasks in the real family
   plan.
3. Identify missing facts that prevent trustworthy recommendations.
4. Define a structured planning-knowledge contract for those facts.
5. Revisit and adapt the existing AI API pipeline to supply that contract.
6. Compare AI-enriched recommendations with the deterministic baseline.

AI-assisted planning knowledge remains an intentional future capability, but
this direction does not authorize resuming the frozen moving-service
experiment, live research, provider calls, credentials, SDKs, or new AI
infrastructure. Deterministic reasoning remains responsible for attention and
Recommendations.

## Keep separate

The Parking Lot retains phase-header Add actions, dependency terminology,
general filters, dependency visualization, alternate views, first-class
People, related-task links, editable phases/categories, and subtasks. Do not
fold those observations into the home-sale walkthrough.

The verified post-migration backup remains outside the repository at
`/home/joeshep/backups/gotime/20260817T001021Z-a32c31d-post-migration/`. Never
add that backup, database files, manifest contents, or family-plan data to Git.

Historical implementation and acceptance details remain in
`SESSION_NOTES.md`.
