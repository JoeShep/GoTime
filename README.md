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

Version 0.0.2 is a single, static screen that proves the core GoTime idea. It
shows one goal, the recommended next step, and a short look ahead. There is no
persistence, authentication, editing, or task-management workflow yet.

## Run locally

With Docker and Docker Compose installed:

```sh
docker compose up --build
```

Open http://localhost:5173 to see the static GoTime experience. The backend
health endpoint remains available at `GET /api/health` as part of the existing
application foundation.

## Documentation

* `docs/product-vision.md` — The long-term vision for GoTime.
* `docs/adr/` — Architecture Decision Records documenting significant technical decisions.
