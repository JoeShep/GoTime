# GoTime

GoTime started with a problem my family needed to solve.

We're planning a move across the country, and it quickly became obvious that this wasn't just a long checklist. We needed to coordinate hundreds of tasks, understand which ones depended on others, assign work to different family members, keep track of progress, and decide what to do first.

We tried existing task management applications. They were good at storing tasks, but they didn't answer the question we cared about most:

> **What should we do next?**

That question became the foundation for GoTime.

GoTime is designed to help people organize, prioritize, and complete meaningful goals. It starts by solving one very specific problem: planning and executing a major relocation. Over time, it will grow into a platform for managing any complex personal or family project, whether that's renovating a house, planning a wedding, starting a business, or preparing for retirement.

The goal is not to create another to-do list. Plenty of applications already do that well.

The goal is to help people make better decisions about their time by showing them the next piece of work that will move them closer to completing a goal.

## Guiding Principles

* Simple enough to use every day.
* Organized around goals instead of isolated tasks.
* Prioritize work based on context, dependencies, and importance.
* Support collaboration between family members.
* Grow through thoughtful, incremental improvements instead of adding features for their own sake.

## Technology

The first version of GoTime will be built with:

* React and TypeScript
* FastAPI
* Docker Compose

Additional technologies will be introduced only when they solve a real problem.

## Current Status

The current MVP slice connects the concept screen to the in-memory reasoning
API. It shows one explained Recommendation and lets the user provide one actual
employment requirement: an acceptable remote, hybrid, on-site, or flexible work
arrangement. That in-memory value changes the engine's reasoning about how to
evaluate candidate locations. For hybrid and on-site work, the user can also
record a maximum acceptable one-way commute in minutes. The engine treats that
value as a hard evaluation boundary, not as an observed or calculated commute.
The user can then provide one free-form likely workplace area, which advances
the Recommendation toward gathering credible travel-time evidence. Finally,
the user can select an intended commute mode: driving, public transit, or
either. `either` means both modes are acceptable and evidence should be
gathered for both, not that the mode is unknown. The submitted mode makes the
manual evidence-gathering Recommendation mode-specific.

GoTime treats the workplace area and travel mode as unverified planning
context. It does not normalize or geocode the area, calculate a route or travel
time, verify a workplace, or score candidate locations. Work arrangement,
commute tolerance, workplace area, and intended mode are only inputs to
employment planning; suitable employment remains an unconfirmed Assumption.
All state remains in memory, with no persistence, authentication, general
editing, or task-management workflow.

## Run locally

With Docker and Docker Compose installed:

```sh
docker compose up --build
```

Open http://localhost:5173 to see the GoTime recommendation experience. The
backend health endpoint remains available at `GET /api/health`.

## Documentation

* `docs/product-vision.md` — The long-term vision for GoTime.
* `docs/adr/` — Architecture Decision Records documenting significant technical decisions.
