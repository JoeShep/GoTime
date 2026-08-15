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