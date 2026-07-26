# Cost and Operational Guardrails

GoTime should remain inexpensive and operationally simple during development, family use, and early testing.

The inclusion of AI, external knowledge, or live research must not turn the application into an unnecessarily expensive or difficult-to-host system.

## Target

For early family and tester use, GoTime should target:

* Approximately **$25–$50 per month or less**
* A configurable hard monthly spending ceiling
* Graceful operation when AI or external research is unavailable

This is a design target rather than a guarantee. Costs should be measured rather than assumed.

## Architectural Principle

> Use deterministic software for work that deterministic software can perform reliably.

GoTime's core should remain responsible for:

* State representation
* Constraint validation
* Date calculations
* Dependencies
* Sequencing
* Decision readiness
* Known domain rules
* Recommendation eligibility
* Contradiction prevention

AI should extend this core rather than replace it.

## AI Usage Principle

> No AI call without a named capability and measurable user benefit.

Appropriate AI capabilities may include:

* Interpreting ambiguous natural-language input
* Suggesting an important missing question
* Applying relevant domain knowledge to the user's circumstances
* Comparing options using grounded evidence
* Explaining tradeoffs in natural language
* Synthesizing current external research

AI should not be used for:

* Routine page rendering
* Simple validation
* Date arithmetic
* Known state transitions
* Every keystroke or form selection
* Repeating an unchanged Recommendation
* Work already handled reliably by deterministic rules

## Knowledge Hierarchy

GoTime should prefer knowledge sources in this order:

### 1. Deterministic Rules

Use explicit code for stable, testable logic.

Examples:

* Whether a deadline has passed
* Whether required information is missing
* Whether a state is contradictory
* Whether one Decision blocks another

### 2. Curated Domain Knowledge

Use maintained, versioned knowledge for information that is relatively stable.

Examples:

* Types of moving services
* Common relocation dependencies
* Questions to ask a moving company
* Typical planning considerations
* Common tradeoffs

### 3. Live External Research

Use current external sources only when freshness materially affects the answer.

Examples:

* Current regulations
* Current provider offerings
* Current pricing or availability
* Recent market conditions
* Current industry guidance

Live research should normally be triggered by a meaningful user action rather than every screen load.

## Research Reuse

Useful external research should be reusable when appropriate.

Store or cache:

* Source
* Retrieval date
* Summary
* Relevant domain
* Freshness or expiration guidance
* Which Recommendation used the evidence

Do not repeat the same research unnecessarily while the evidence remains sufficiently current.

## Model Selection

Use the least expensive model that can reliably perform the named capability.

Prefer:

* Smaller or less expensive models for classification, extraction, and constrained suggestions
* Stronger models only for genuinely difficult interpretation or synthesis
* Structured outputs where possible
* Bounded prompts and bounded responses

Do not repeatedly send the user's entire Goal history when a focused context package is sufficient.

## Usage Controls

Before broad use, GoTime should support:

* Monthly AI spending limits
* Per-user or per-goal usage limits
* Maximum prompt size
* Maximum response size
* Cost logging by capability
* Request counts by capability
* Cached or reused research
* Explicit confirmation before expensive operations
* A deterministic fallback when AI is unavailable

## Background Activity

The MVP should not include autonomous background AI agents.

Background monitoring or recurring research should only be introduced when:

* It solves a demonstrated user problem
* Its cost is measurable
* Its frequency is bounded
* The user has explicitly enabled it
* A less expensive event-driven or scheduled alternative is insufficient

## Hosting Principle

Prefer the smallest maintainable deployment that supports current usage.

Avoid:

* Premature microservices
* Oversized cloud instances
* Always-running workers without demonstrated need
* Separate infrastructure for capabilities that can remain in one service
* Managed services whose cost exceeds their current value

The initial React and FastAPI architecture, along with any database introduced
when persistence is justified, should remain deployable on modest
infrastructure.

## Review Questions

Before proposing or implementing a new capability, ask:

* Can deterministic code solve this reliably?
* Does this require current external information?
* Can curated knowledge solve it without live research?
* Does AI add a meaningful capability or only rewrite text?
* How often will this operation run?
* What is the estimated cost per use?
* Can the result be cached or reused?
* What happens when the AI or external source is unavailable?
* Does the design preserve a clear monthly spending ceiling?
* Is the operational complexity justified by demonstrated value?

## Definition of Done for AI-Assisted Features

An AI-assisted capability is not complete until:

* Its purpose is named.
* Its inputs are bounded.
* Its output is structured or testable.
* Its grounding is visible.
* Its estimated cost is understood.
* Its usage can be measured.
* Its failure behavior is defined.
* Its result does not silently become trusted user state.
* A deterministic fallback or safe failure path exists.
