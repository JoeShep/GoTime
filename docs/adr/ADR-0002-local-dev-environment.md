# ADR-0002: Use Docker Compose for Local Development

## Status

Accepted

## Context

GoTime consists of multiple services, including a React frontend and a FastAPI backend.

Developers should be able to clone the repository and run the application with minimal machine-specific configuration. The development environment should be consistent across Windows, macOS, and Linux.

## Decision

The project will use Docker Compose as the standard local development environment.

Each service will define its own Dockerfile, and Docker Compose will orchestrate startup, networking, and health checks.

The frontend will communicate with the backend using Docker networking rather than localhost-specific configuration.

## Consequences

Positive:

- Consistent development environment across platforms.
- Reduced onboarding effort.
- Production-like networking during development.
- Service dependencies can be managed through Docker health checks.

Negative:

- Slightly slower startup than running services directly.
- Docker Desktop is required for local development.