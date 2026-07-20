# Session Notes

## Session 0 -- Workstation

### Completed

- Built WSL2 workstation
- Configured Git
- Configured GitHub SSH
- Installed Oh My Zsh
- Installed Starship
- Created workstation repository

### Lessons

- Inspect before changing.
- Document decisions.
- Keep configuration intentional.

I think we've discovered our project documentation hierarchy

This is the structure I'd like us to use consistently:

README.md
    ↓
What is this project?

ADR
    ↓
Why did we make major decisions?

Architecture docs
    ↓
How is the project organized?

SESSION_NOTES.md
    ↓
What happened over time?

NEXT_SESSION.md
    ↓
What are we doing next?

TODO.md
    ↓
What remains to be done?

---

## Session 1
Here's the workflow I'd like us to adopt
+ Review NEXT_SESSION.md (our current objective).
+ Review TODO.md (anything still outstanding).
+ Make any adjustments based on what we've learned.
+ Execute the plan.
+ Update SESSION_NOTES.md.
+ Commit.

Here's how I'd like our first coding session to go

Not "today we're going to scaffold React."

Instead:

Today we're going to prove that the architecture works.

By the end of the session, I want us to have:

A gotime repository with a clean structure.
React (TypeScript) running.
FastAPI running.
Docker Compose starting both.
The React frontend making an HTTP call to FastAPI.
The browser displaying "Hello, GoTime!" from the backend.
Everything committed.

That will be our Version 0.0.1.

It's tiny, but it's real.
...

---

## Session 2 -- Application Bootstrap

### Completed

- Corrected the `make session` command to use `scripts/begin.sh`.
- Added a Vite, React, and TypeScript frontend.
- Added a FastAPI backend with `GET /api/health`, returning `{ "status": "ok" }`.
- Added one root `docker-compose.yml` for the frontend and backend.
- Configured the frontend to call `/api/health` and display the backend status.
- Verified the frontend production build and backend Python syntax.

### Pending

- Docker Compose runtime verification could not run on this workstation because
  Docker is not installed.
- Make the initial commit after that verification.

---

## Session 3 -- Version 0.0.2 Concept Screen

### Completed

- Reframed the current milestone around proving GoTime's central question:
  "What should I do next?"
- Replaced the frontend health-check placeholder with a single static screen.
- Presented a hard-coded relocation goal, one recommended next step, and two
  upcoming steps.
- Explicitly deferred persistence, authentication, editing, and task-management
  workflows.
- Kept the FastAPI health endpoint and Docker Compose foundation in place for
  later iterations.

### Next

- Put the screen in front of its intended user and learn whether the recommended
  next step feels immediately useful.

---

## Session 4 -- Frontend Development Workflow

### Completed

- Adopted React-Bootstrap, Bootstrap utilities, and SCSS as frontend
  conventions, with the decision recorded in ADR-0003.
- Refactored the concept screen to use React-Bootstrap components and
  project-specific SCSS modules for shared variables and mixins.
- Configured Docker Compose for frontend live reload using a source bind mount,
  a container-managed `node_modules` volume, and file-watch polling.
- Verified the running frontend container uses the source bind mount and runs
  Vite in development mode.

### Next

- Define GoTime's domain language—Goal, Project, Task, Milestone, and
  Dependency—before designing a database or additional infrastructure.

## Session 5 -- 'Whiteboarding', or how I went from a todo app to a reasoning engine
(this is copied straight from CGPT's response to my attempt to explain what I wanted to app to do for us)

I think we need to define the engine's responsibilities
If I were writing them today, they'd be:
+ Understand -- What is the user trying to accomplish?
+ Model -- Build a representation of the plan.
+ Predict -- Estimate durations, dependencies, and risks.
+ Monitor -- Watch for changes.
+ Adapt -- Recalculate when something changes.
+ Recommend -- Answer: What should I do next?
+ Explain -- Perhaps the most important responsibility. Never just say: "Do this." Always answer: Why?

This leads to an important realization

I don't think "AI" belongs everywhere.

I think AI belongs primarily in these places:

+ building an initial plan,
+ estimating timelines,
+ identifying missing work,
+ explaining recommendations,
+ summarizing progress,
+ answering questions.

Everything else should be deterministic. For example: Task assignments. Permissions. Notes. Attachments. Those don't need AI.

If we can define how GoTime reasons, then every subsequent decision becomes easier:

+ The domain model exists to support the reasoning engine.
+ The database exists to persist the domain model.
+ The UI exists to expose the reasoning engine.
+ AI exists to enhance the reasoning engine.

I think GoTime has three kinds of knowledge.

1. Facts
Things the user tells us.

Examples:
+ Move date
+ Family members
+ Budget
+ House under contract

2. Rules
Things GoTime knows.

Examples:
+ Movers should usually be booked 8–12 weeks in advance.
+ Utility transfers should occur shortly before occupancy.
+ Vehicle registration deadlines vary by state.

3. Inference
What GoTime concludes.

Examples:
You should schedule movers this week.
or
This task is blocked because closing has not occurred.

That separation is powerful because it means we can improve the reasoning engine without changing the user's data.

We decided to design the reasoning engine by role-playing real planning conversations rather than starting with a database schema. The conversation itself will be treated as a source of requirements for the engine.

Session 6 -- The API acted as a project mgr and asked me questions about our move. It resulted in some changed ideas about how this app will behave

Here's the complete list of ideas I think we generated today
New concepts
Strategic Reasoning
Operational Reasoning
Decision Filters
Decision Readiness
Backward Planning
Sequencing Engine
Continuous Re-evaluation
Recommendation Transparency
Conversation Engine
Plan Invalidation
Waiting for Information
Refined concepts
Constraints → Decision Filters
Tasks → Outputs of reasoning
Projects → Vehicles toward goals
Recommendations → Explained recommendations
Risks → Inputs into reasoning rather than standalone objects
Important distinctions

### Action
> Something someone does.

### Decision
>Something someone chooses.

### Event
>Something that happens.

Those three affect sequencing differently.

### Waiting vs Blocked
Another subtle distinction.

Blocked: Can't continue because prerequisite work isn't complete.

Waiting: Can't continue because external information hasn't arrived.

Very different reasoning.

### Assumptions

These became first-class citizens.

Examples:
+ house sells
+ spouse finds employment
+ destination remains unchanged

The engine should know these are assumptions rather than facts.

### Plan Invalidation
We distinguished ordinary risks from events that should cause the engine to stop optimizing the current plan and instead reconsider it from the ground up.

### Success Factors
I'm actually least confident about this one.

The examples you gave—your spouse finding meaningful work and access to high-quality healthcare—could fit under "Definition of Success" instead of becoming a separate concept.

I'd hold off on creating a new category until we see whether it recurs in other domains.

---

## Session 7 -- First In-Memory Reasoning Loop

### Completed

- Added minimal in-memory models for Goal, SuccessCriterion, Constraint,
  Preference, Decision, Assumption, and Recommendation.
- Represented one hard-coded Tennessee-to-Northern-California relocation
  scenario.
- Added one deterministic, relocation-specific rule that recommends clarifying
  spouse employment requirements before selecting a final target location.
- Included why, why now, relevant dependencies, blocked downstream work, and
  the related employment Assumption in the Recommendation.
- Exposed the primary Recommendation at
  `GET /api/recommendations/primary`.
- Added focused reasoning and endpoint tests.

### Modeling Decisions

- Explanation remains embedded in Recommendation, as anticipated by the domain
  model.
- Decision readiness and Assumption status use only the states needed by this
  scenario.
- Downstream work and dependencies remain descriptive values. No generic rule
  engine, dependency graph, persistence layer, or Action model was introduced.
- No ADR was needed because these choices follow the existing MVP and domain
  documentation.

### Verification

- Backend tests: 3 passed.
- Python compilation: passed.
- Whitespace validation with `git diff --check`: passed.
- Docker verification passed: `GET /api/health` returned `{"status":"ok"}` and
  `GET /api/recommendations/primary` returned the expected updated contract.

### Next

- Review the first recommendation payload and decide whether it is the right
  contract for the first frontend-backed reasoning experience.

---

## Session 8 -- State Change and Re-Reasoning

### Completed

- Added the minimum relocation-specific state needed to distinguish unclear
  from clarified spouse employment requirements.
- Derived the clarified Goal snapshot from the original with `model_copy`
  without mutating the original snapshot.
- Preserved the original Recommendation for unclear requirements.
- Added a second deterministic Recommendation to evaluate candidate locations
  against clarified employment requirements.
- Preserved the unconfirmed suitable-employment Assumption and the structured
  relationship to the `target-location` Decision in both Recommendations.
- Added the temporary `employment_requirements` query parameter; omitted and
  `unclear` values are equivalent, while `clarified` selects the second proof
  snapshot.
- Added explained HTTP 422 responses for unsupported query values and
  recognized states without an applicable reasoning path.

### Modeling Decisions

- `EmploymentRequirementsStatus` and
  `Goal.relocation_employment_requirements_status` are relocation-specific
  scenario state for this proof, not finalized universal Goal fields.
- A broader CurrentState model, generic fact system, persistence layer, state
  manager, rule engine, and dependency graph remain deferred.
- Clarifying requirements does not validate the separate Assumption that
  suitable employment exists in a viable candidate region.
- No ADR was needed because the temporary query contract and scenario state do
  not establish durable production architecture.

### Verification

- Backend tests: 10 passed.
- Python compilation: passed.
- Whitespace validation with `git diff --check`: passed.
- Docker Compose rebuilt successfully; the backend was healthy and the
  frontend started.
- Docker endpoint checks passed for health, default, unclear, clarified, and
  unsupported-query behavior.

### Next

- Review the two-state reasoning flow and API proof before committing.

---

## Session 9 -- Frontend Recommendation Integration

### Completed

- Replaced the static recommendation and upcoming-step content with the live
  primary Recommendation returned by the backend.
- Added endpoint-specific TypeScript models and one focused fetch function.
- Displayed what is recommended, why, why now, relevant dependencies, blocked
  downstream work, and the related employment Assumption.
- Added a visually secondary temporary scenario control for unclear and
  clarified spouse employment requirements.
- Added loading and error states.
- Prevented obsolete requests from replacing the result for the latest selected
  state through request cancellation and a current-request guard.
- Kept `related_decision_id` and other implementation identifiers out of the
  rendered interface.
- Added focused frontend component tests and development-only test tooling.

### Modeling and UI Boundaries

- The scenario selector demonstrates state change; it is not a proposed
  production editing workflow and does not persist anything.
- Clarified employment requirements remain distinct from the unconfirmed
  Assumption that suitable employment exists.
- No routing, global state manager, forms infrastructure, generalized API
  client, or backend change was introduced.
- No ADR was needed because the integration follows the established frontend
  conventions and uses a temporary proof control.

### Verification

- Frontend tests: 5 passed.
- Frontend production build: passed.
- Backend tests: 10 passed.
- Backend Python compilation: passed.
- Docker Compose rebuild passed; the backend was healthy and the frontend was
  running.
- The frontend proxy returned the expected unclear and clarified contracts.
- Whitespace validation with `git diff --check`: passed.

### Next

- Review the live experience with its intended user before selecting the next
  milestone.
