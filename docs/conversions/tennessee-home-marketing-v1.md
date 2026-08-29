# Tennessee home-marketing conversion v1

This narrow conversion rehearses the first real Milestone/Decision family-plan
change on an isolated copy only. It makes no schema change and must not be run
against the active database without separate authorization.

## Deployment status

Human review and isolated rehearsal passed, and the separately authorized
active conversion was applied on August 28, 2026 from accepted commit
`a62cad8fbfdcbb4a1139fdc7629612c09340f28c`. The active rerun returned
`unchanged`. Production backup, manifest, restore, rehearsal, and post-startup
evidence are preserved under
`/home/joeshep/backups/gotime/20260828-first-family-conversion-closeout/`.
This repo-external directory is the authoritative durable backup. The identical
`/tmp/gotime-family-conversion-production-backup-20260828/` copy remains
temporarily available but is not authoritative. Restore-rehearsal volume
`gotime_family_conversion_restore_rehearsal_20260828` also remains retained.
Those historical backup files, manifests, checksums, and restore evidence
remain immutable records of the conversion as originally applied.

## Approved copy correction

The subsequent deterministic-ranking acceptance correction replaces only the
description on exact Milestone `put-tennessee-home-on-market-2027` with the
approved family-facing achievement language. The narrow transactional artifact
is `scripts/conversions/correct_tennessee_milestone_description.py`. It accepts
only the exact historical description (applied) or the exact approved new
description (unchanged), validates identity, window, pending state, and target
uniqueness, and otherwise fails without mutation. Its isolated acceptance
manifest is retained at
`/tmp/gotime-tennessee-milestone-description-v2-acceptance.json`; this new
evidence does not alter the immutable v1 production evidence.

The separately authorized correction was applied to production on August 29,
2026 during deterministic-ranking closeout. Active checksum changed from
`f33aa79f83218fed3246133a639c232892bb8c7211e7b5b92aad8015ed076e1c` to
`5fd96cf175ea2af93ff50d22d890d436fbc4e4588c5608ef8388cfcd1dd3071f`
for the transactional field update. Normal repository initialization then
advanced only SQLite header bytes 28 and 96, producing
`496eba140d5684a6458efebdddf5ccc1ff7da9f810cca236b0d3b794bd374df5`;
an isolated initialization reproduced that file byte-for-byte. Counts and every
stable hash except `milestones` remained identical. The new authoritative
backup and audit record is
`/home/joeshep/backups/gotime/20260829-deterministic-ranking-closeout/`, and
restore volume `gotime_deterministic_ranking_restore_rehearsal_20260829` is
retained. The immutable 20260828 evidence remains untouched.

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
Their canonical display titles are **List publicly**, **Seek builder offers
directly**, and **Pursue both paths**; the Milestone achievement description
uses those same titles. These accepted labels are not deployment-time aliases.
Only the reused parent is linked as Decision preparation.

Child order is Prepare questions, Contact, Schedule, Meet. Schedule depends on
Contact. Meet depends on Schedule and Prepare questions. All children are in
`prepare`, have Housing and Anne/Joe, and use neutral medium priority without
invented dates. Neither the parent's High priority nor its cleared dates are
copied to them. The parent has automatic derived status and no override. Manual
priority across the family plan remains deferred to deterministic-attention
calibration.

The January 4–15, 2027 Milestone window remains editable user-provided planning
data, not a forecast. Fresh conversions now use this approved description:
“Mark this milestone achieved when the public listing is live, the property has
been offered directly to selected builders, or—if pursuing both paths—both have
begun. Meeting with the realtor or choosing a marketing option alone does not
achieve it.”

## Operation and safety

Run `scripts/conversions/convert_tennessee_home_marketing.py DATABASE
--manifest MANIFEST` only against the approved isolated copy. The conversion
uses one immediate transaction, exact stable IDs, foreign-key enforcement,
post-write target validation, and an unrelated-row baseline projection. A
complete target is a no-op on rerun. Changed sources and partial targets fail
closed; any exception rolls back the transaction. The generated JSON manifest
records before/after checksums, counts, hashes, reused records, and created IDs.
