# GoTime
GoTime helps people make better decisions while pursuing complex goals by combining strategic reasoning with operational sequencing.

It began with a simple question:

> **What should we do next?**

GoTime is designed to help people organize, prioritize, and complete meaningful goals. It starts by solving one very specific problem: planning and executing a major relocation. Over time, it will grow into a platform for managing any complex personal or family project, whether that's renovating a house, planning a wedding, starting a business, or preparing for retirement.

The goal is not to create another to-do list. Plenty of applications already do that well.

The goal is to help people make better decisions about their time by showing them the next piece of work that will move them closer to completing a goal.

## The First Real User

GoTime did not begin as an idea for a productivity application.

It began with a real problem.

My family is planning a move across the country. As we started planning, we realized the challenge wasn't simply keeping track of tasks. The challenge was understanding priorities, dependencies, timing, and deciding what to do next.

That relocation became the first real project GoTime was designed to support.

Because of that, every proposed feature should answer a simple question:

> **Would this have made planning and executing our move easier?**

If the answer is yes, the feature is probably aligned with GoTime's purpose.

If the answer is no, we should carefully consider whether it belongs in the product.


Guiding Principles
+ Simple enough to use every day.
+ Organized around goals instead of isolated tasks.
+ Prioritize work based on context, dependencies, and importance.
+ Support collaboration between family members.
+ Grow through thoughtful, incremental improvements instead of adding features for their own sake.

## Project Goals

The first milestone is to establish a solid application architecture before implementing core features.

The initial technology stack includes:

* React with TypeScript
* FastAPI
* Docker Compose

Additional technologies will be introduced only when they solve a real problem.

## Documentation

* `docs/adr/` - Architecture Decision Records documenting significant technical decisions.
* `docs/product-vision.md` - The long-term vision for GoTime.
* `docs/reasoning-engine.md` - Defines how GoTime thinks
* `docs/capability-roadmap.md` - Defines what the reasoning engine can be expected to do, and where the dividing lines are between the AI and the app (For lack of a better way to put it)

Vision tells us why.
Reasoning Engine tells us what the engine must be capable of thinking about.
Capability Roadmap tells us what we build next to realize that vision.
The code implements those capabilities.