# ADR-0012: Derive contextual Recommendation signals from the current Plan

## Status

Accepted for the contextual Decision-preparation Recommendation candidate.

## Context

Decision preparation must affect what GoTime recommends without turning a
relationship into an unconditional priority boost, recommending parent
summaries or blocked work, or embedding explanation text inside opaque sorting.
The current Plan aggregate already projects effective Task status, hierarchy,
dependencies, dates, Decision readiness, and preparation links. No additional
persisted fact is required.

## Decision

Build Recommendation candidates and structured signals deterministically from
one current Plan snapshot. Candidates are actionable Tasks and unresolved
Decisions that are ready to decide. Signals identify ready Decisions, direct or
parent-inherited preparation, and actionable prerequisites that unblock
preparation. Each signal carries stable Decision identity plus relevant parent,
preparation-Task, blocked-Task, and dependency-path context.

This ADR documents the implementation and extensibility boundary. The
[Recommendation hierarchy](../reasoning-engine.md#recommendation-hierarchy) is
the authoritative behavioral explanation and visualization.

Eligibility and hard constraints remain separate from signals. Completed,
blocked, future-start, inactive, and parent-summary Tasks are not eligible.
Traversal through blocked preparation stops at every currently actionable
prerequisite frontier, expands an incomplete parent prerequisite through its
actionable subtasks, and never crosses an inactive Task. A preparation signal
affects a Task's rank once even when several unresolved Decisions apply; all
applicable Decision contexts remain available for explanation.

Preserve the existing Task comparison factors. Priority, supported due-date
ordering, work already in progress, direct-unblocking leverage, phase order,
and stable identity retain their established meanings. Context breaks ties
within the same existing attention factors in this order: ready Decision,
signaled Task, ordinary Task. Downstream preparation due dates may contribute
timing pressure to an actionable prerequisite, but blocked work never becomes
eligible. Ready Decisions use the neutral existing baseline of medium priority,
no due date, and not started.

The API returns a primary item and bounded upcoming items using the same
candidate contract. Task and Decision targeting reuse Plan's transient reveal,
focus, and highlight mechanism. Mutations continue to return the updated Plan;
the client refetches Recommendations immediately from that response boundary.

Task activation is an additive, nonpersistent Plan projection that currently
defaults to active. This slice does not implement conditional activation or
reveal hidden work; it only makes the Recommendation traversal fail closed when
an inactive projection is present.

## Extensibility boundary

Deterministic rules always own eligibility and hard constraints. Future curated
or AI-derived inputs may influence ranking only through this structured signal
boundary, and Recommendations must remain usable when AI is unavailable. No AI
call, research, confidence field, provenance record, or persistence is added
here. Before any AI-derived signal is used in production, its provenance,
confidence, freshness, and user-override semantics require separate design and
approval.

## Consequences

Recommendation explanations are derived from inspectable context rather than
being the source of ranking truth. Recalculation is immediate and stateless.
The family database and existing Decision, hierarchy, dependency, and Task
records remain unchanged.
