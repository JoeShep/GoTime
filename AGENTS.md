# AGENTS.md

This document describes how contributors, both human and AI, should collaborate on the GoTime project.

When in doubt, optimize for clarity over cleverness.

## Session Startup Checklist

At the beginning of each new feature, milestone, or planning session:

* [ ] Read `README.md`
* [ ] Read `NEXT_SESSION.md`
* [ ] Read `TODO.md`
* [ ] Review all ADRs if there are fewer than five.
Otherwise review the most recent five.
* [ ] Review `docs/product-vision.md`
* [ ] Review `docs/parking-lot.md` for ideas that should be promoted into the current milestone. If the Parking Lot is empty, simply state that no ideas are awaiting promotion.
* [ ] If any required document is missing, mention it before proposing a plan.
* [ ] Confirm today's objective before making changes.

## Frontend Conventions

Unless a specific task requires otherwise:

* Use React-Bootstrap components and Bootstrap utility classes for layout and styling.
* Use SCSS for custom styling. Avoid plain CSS files.
* Prefer Bootstrap utility classes over custom SCSS when they provide the desired result.
* Create custom SCSS only when Bootstrap cannot achieve the design cleanly.
* Keep styling consistent with the project's clean, functional aesthetic.
* Favor reusable React components over duplicated markup.

## Working Style

* Inspect before changing.
* Understand before automating.
* Explain significant tradeoffs before implementation.
* Prefer maintainable solutions over clever ones.
* Keep changes focused and well documented.
* Leave the project in a better state than you found it.

## Documentation Rules

* Significant technical decisions require an ADR.
* Product direction belongs in `docs/product-vision.md`.
* New ideas that are not part of the current plan belong in `docs/parking-lot.md`.
* The Parking Lot is a place to preserve ideas, not a commitment to implement them.
* Promote ideas from the Parking Lot only after they have been intentionally selected for the current milestone.

## Philosophy

GoTime is a goal execution platform, not simply a task management application.

Every feature should help answer the question:

> "What should I do next?"

## Questions

Before implementing a significant feature, ask:

* Is this solving a real user problem?
* Would this have helped with the family move?
* Does it make it easier to decide what to do next?
* Is there a simpler approach?

## Definition of Done

Work is considered complete when:

* The feature works as intended.
* Documentation has been updated.
* Any significant decisions have been recorded.
* The project builds successfully.
* All completed work has been committed.

## Session Shutdown Checklist

* [ ] Update `SESSION_NOTES.md`.
* [ ] Update `NEXT_SESSION.md`.
* [ ] Add new ideas to `docs/parking-lot.md`.
* [ ] Write an ADR if a major decision was made.
* [ ] Commit all completed work.
* [ ] Verify the project still builds and runs.
