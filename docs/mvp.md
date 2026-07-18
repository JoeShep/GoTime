This document should become the contract for v0.1.

## Goal

Demonstrate that GoTime can reason about a complex goal, recommend the next decision or action, and explain its reasoning in a way the user trusts.

The MVP is not intended to prove:

+ scalability
+ collaboration
+ AI sophistication
+ production architecture

It is intended to answer one question:

> Does the reasoning engine create enough value that someone would want to keep using it?

## Target User
One user.

One goal.

For the MVP, that user is you.

Specifically:

> Someone planning a complex move from Tennessee to California.

Why?

Because we already understand this domain deeply, have real data, and can immediately tell when recommendations feel wrong.

Future domains (retirement, weddings, renovations, etc.) are intentionally out of scope.

## Core User Journey
1. Create Goal

2. Describe Situation

3. Engine Builds Internal Model

4. Engine Produces Recommendation

5. Engine Explains Recommendation

6. User Updates Situation

The critical thing to validate is Step 6. When the user changes something -- "We selected a city." -- the engine should update its recommendations. That demonstrates continuous reasoning rather than static planning.

## MVP Inputs

The user provides enough information for the engine to reason.

Examples:
+ Goal
+ Definition of Success
+ Current State
+ Decision Filters
+ Open Decisions
+ Assumptions
+ Risks

Not every field has to exist in v0.1, but these are the categories we expect to support.

## MVP Outputs

The engine produces:

Primary

One recommended next step.

Example:

> Decide on your target city.

### Supporting explanation
+ Why this recommendation?
+ What is blocked?
+ What assumptions does it depend on?
+ What happens after this?

## Reasoning Scope

For the MVP, the engine only needs to perform a handful of reasoning tasks.

+ recognize blocked work
+ recognize waiting states
+ respect non-negotiable constraints
+ identify decision readiness
+ understand simple dependencies
+ explain recommendations

## Explicitly Out of Scope

This is just as important.

No:
+ authentication
+ collaboration
+ multiple users
+ notifications
+ calendar integration
+ email integration
+ mobile application
+ reporting
+ dashboards
+ attachments
+ permissions
+ multiple simultaneous goals   

## Success Criteria
### Functional

The user can:
+ create a goal
+ describe their situation
+ receive a recommendation
+ understand why
+ change information
+ observe the recommendation update

### Qualitative

The user should say:
> "That recommendation makes sense."

or

> "I hadn't thought of that."

Those are stronger validation than "the code works."

## The Vertical Slice
Instead of building "an app," let's build one complete reasoning loop.

Goal

↓

Capture

↓

Represent

↓

Reason

↓

Recommend

↓

Explain

↓

User changes something

↓

Re-reason

## MVP Non-Goals

These are things the MVP should not attempt.

For example:
+ Be generally intelligent.
+ Handle every planning domain.
+ Automatically discover every dependency.
+ Produce perfect recommendations.

Instead, the MVP should demonstrate that the architecture is sound and that the reasoning process feels useful.

## No more focus on tasks
build around recommendations.

That means the main screen isn't "My Tasks."

It's something like:

> Today's Recommendation: 
> Choose your target city.

Why?

Because housing selection, realtor selection,
school research, and commute analysis all
depend on this decision.

> Blocked Until  
 > • Neighborhood selection   
 > • Home search   
> Waiting On   
 >• Spouse employment information

### Version 0.1 is complete when a user can enter one complex goal, receive a trusted recommendation with a clear explanation, update their situation, and see the recommendation change appropriately.