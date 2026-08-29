AI Contributor Experience (A feature of the repository, not of GoTime)
Over time, I'd love to refine how AI collaborators interact with the project. Things like:

Better AGENTS.md conventions.
Session scripts.
Prompt libraries.
Automated project summaries.
Architectural review prompts.

Development environment

As GoTime grows, split Docker Compose configuration into:

- `docker-compose.yml`
- `docker-compose.dev.yml`

### Future GA security hardening: 
The current GoTime architecture is appropriate for development, friends-and-family use, and bounded evaluation. Before general availability or exposure to untrusted users, perform a dedicated security/threat-model review and design production-grade authentication, authorization, secrets management, persistence/transaction guarantees, audit integrity, abuse/rate limiting, backup/recovery, and monitoring. The current offline hash-chained evaluation history should not be assumed to provide production tamper resistance.
Revisit when GoTime moves from trusted friends/family use toward a public beta or GA.

### User-defined project phases

Phases should eventually be configurable per project rather than hard-coded
around relocation. Users should be able to create, rename, reorder, and remove
phases as their understanding of a project evolves. GoTime may offer useful
starter/default phases during project setup.

### User-defined categories

Categories should eventually be configurable per project. Users should be able
to create, rename, reorder, and remove categories, and GoTime may offer useful
project-specific defaults. The current relocation categories are defaults, not
a permanent ontology.

### Advanced subtasks / task hierarchy

The home-sale walkthrough selected one level of required subtasks for its
proposed initial slice, with reversible parent status derived from those
subtasks. More general hierarchy remains future work: nested and optional
subtasks, creating a subtask directly under another Task, reassigning a
top-level Task under a parent, and the exact direct parent-status override.
Parent/subtask hierarchy remains distinct from dependency/blocking
relationships.

### Removing incomplete work

A user may decide that an incomplete Task is no longer applicable. Before
removing it, GoTime should inspect and present its relationships, including:

* incoming and outgoing dependencies;
* parent and subtask relationships;
* Decisions it informs;
* conditional branches it belongs to; and
* Milestones it supports.

GoTime must not silently remove a dependency and make downstream work appear
ready. Future design should distinguish **Remove from plan**, **No longer
applicable**, and **Permanent deletion**. Their exact semantics, reversibility,
history, and safety interactions remain unresolved and are not part of the
current implementation-slice proposal.

### Relocation-plan UX observations

Keep these observations separate from the selected derived-attention milestone:

* Add-task actions in phase headers with phase-prefilled creation.
* Friendlier dependency terminology.
* Minor mobile page-shell spacing inconsistencies remaining after the accepted
  Now/Plan navigation work; revisit as visual polish after the functional
  navigation sequence is complete.
* Validate native date-picker reliability on a real mobile browser; do not
  replace the native input based only on Firefox Responsive Design Mode.
* Mobile now has its selected persistent bottom navigation; separately
  reconsider persistent desktop access to Now, Plan, and Find while deep in a
  long Plan after the current non-sticky navigation has broader use.
* General task filters beyond the existing category filter and plan-wide
  finder.
* Dependency visualization.
* Alternate plan views.
* First-class People and assignment identities.
* Non-blocking related-task links.
* After editing, optionally highlight the specific field and value that changed;
  keep this distinct from the accepted return-to-Task location highlight. This
  remains deferred after deterministic-ranking closeout.

These remain useful candidates, but none is part of the current product-design
objective.

### Plan header and future plan management

The current Plan header repeats navigation context and uses generic or
implementation-oriented wording: **Plan** is already communicated by
navigation, **Family plan** is generic while only one plan exists, and
**Persistent plan** does not help the user. The persisted goal title is the
meaningful content.

Future direction is to simplify the header around a generic **Our goal** label
and the persisted, user-defined goal title. A proper plan lifecycle should let
the user create and later rename that goal, display it consistently on Now and
Plan, and may add a compact dynamic summary such as remaining, in-progress, and
completed work. Reserve a plan name such as **Family plan** for a future plan
selector if GoTime supports multiple plans.

Do not redesign the current header until plan lifecycle and multi-plan
direction are defined; avoid polishing the interface around incomplete
assumptions. This is deferred product/UX direction, not the next increment.

### Operational cleanup

* Eliminate SQLite byte-level writes from no-op backend repository
  initialization while preserving idempotent schema validation and startup.
