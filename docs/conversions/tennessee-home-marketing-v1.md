# Tennessee home-marketing conversion v1

This narrow conversion rehearses the first real Milestone/Decision family-plan
change on an isolated copy only. It makes no schema change and must not be run
against the active database without separate authorization.

## Approved source

The source is the post-contextual-Recommendations family database with SHA-256
`09bf1f9c2453254c0319b58d1bd3beb59bc8c37f4701bdb6269d0b87749f9f7a`.
It contains 49 Tasks and no Milestones, Decisions, options, preparation links,
hierarchy links, or parent-status overrides. The script validates both this
file checksum and stable hashes for every logical table before writing.

The sole reused Task is
`reengage-with-tn-realtor-e71dd74d-01e4-4338-9a94-0570bec0f3d2`, originally
**Reengage with TN realtor**. It is in `prepare` (**Prepare for the move**), is
not started, high priority, starts 2026-08-13, is due 2026-09-01, has Housing,
is assigned to Anne, has no description or hierarchy, and is depended on by
three existing Tasks. Those fields and dependency edges are preserved except
for its approved title, the addition of Joe, and clearing both dates. The dates
were temporary UI-test data, so removing them is an explicit approved mutation,
not inferred cleanup or loss of user planning data. The parent's meaningful
legacy High priority is preserved. Anne and Joe are the dominant existing
family and Housing assignee pair. No plausible existing Task matched any
required child title, so all four children are created.

## Target and stable identities

The script creates Milestone `put-tennessee-home-on-market-2027`, Decision
`choose-how-to-market-our-home`, and four children with IDs matching their
normalized approved titles. It creates the three ordered options with IDs
`list-publicly`, `seek-builder-offers-directly`, and `pursue-both-paths`.
Only the reused parent is linked as Decision preparation.

Child order is Prepare questions, Contact, Schedule, Meet. Schedule depends on
Contact. Meet depends on Schedule and Prepare questions. All children are in
`prepare`, have Housing and Anne/Joe, and use neutral medium priority without
invented dates. Neither the parent's High priority nor its cleared dates are
copied to them. The parent has automatic derived status and no override. Manual
priority across the family plan remains deferred to deterministic-attention
calibration.

The January 4–15, 2027 Milestone window is editable user-provided test data,
not a forecast. Its description records that achievement requires explicit
user confirmation after the selected marketing path has begun; meeting with
the realtor or selecting an option is insufficient.

## Operation and safety

Run `scripts/conversions/convert_tennessee_home_marketing.py DATABASE
--manifest MANIFEST` only against the approved isolated copy. The conversion
uses one immediate transaction, exact stable IDs, foreign-key enforcement,
post-write target validation, and an unrelated-row baseline projection. A
complete target is a no-op on rerun. Changed sources and partial targets fail
closed; any exception rolls back the transaction. The generated JSON manifest
records before/after checksums, counts, hashes, reused records, and created IDs.
