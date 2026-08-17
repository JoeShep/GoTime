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

### Subtasks / task hierarchy

Tasks should eventually be able to contain subtasks. A task may be created
directly under an existing task or later reassigned from top-level to become a
subtask. Parent/subtask hierarchy is distinct from dependency/blocking
relationships. Do not decide yet whether parent completion automatically
depends on subtask completion.

### Relocation-plan UX observations

Keep these observations separate from the selected derived-attention milestone:

* Add-task actions in phase headers with phase-prefilled creation.
* Friendlier dependency terminology.
* General task filters beyond the existing category filter and plan-wide
  finder.
* Dependency visualization.
* Alternate plan views.
* First-class People and assignment identities.
* Non-blocking related-task links.

These remain useful candidates, but none is part of the current product-design
objective.
