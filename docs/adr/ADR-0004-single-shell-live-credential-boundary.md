# ADR-0004: Keep live credential entry and provider launcher in one operator shell

## Status

Accepted for the controlled moving-service preflight pilot.

## Context

An interactive credential exported in a human operator's zsh cannot be
inherited by a command launched later from Codex's separate process. Sequence 2
therefore closed before credential lookup even though the operator had entered
the key correctly.

## Decision

Each future live preflight sequence uses one fixed, capability-specific zsh
operator script. The human runs it directly. It validates active authority,
prompts silently, exports the evaluation-specific credential and fixed controls
inside the same process tree, invokes the fixed Docker child once, verifies or
recovers closure, and unsets all variables through traps.

Credentials are never accepted as arguments or files. Codex does not launch
the live operator script. Synthetic tests inject input only behind an explicit
network-disabled test boundary.

## Consequences

- Shell inheritance is deterministic and testable.
- Credential values do not cross chat, argument, or filesystem boundaries.
- Closure and variable cleanup cover success, failure, and interruption.
- Each sequence still requires a distinct candidate, reviewed authorization,
  atomic activation, and separate live-call approval.
