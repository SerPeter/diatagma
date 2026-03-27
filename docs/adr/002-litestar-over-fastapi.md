# ADR-002: Use Litestar over FastAPI for the web API

## Status

Accepted

## Context

Diatagma needs a Python web framework to serve the JSON API consumed by the React dashboard. The main candidates were:

1. **FastAPI** — most popular async Python web framework, Pydantic-native
2. **Litestar** (formerly Starlite) — performance-focused alternative, also Pydantic-native, built on its own ASGI foundation

Both support async, Pydantic models, OpenAPI generation, and dependency injection.

## Decision

Use **Litestar** as the web API framework.

## Consequences

### Positive

- Higher throughput than FastAPI in benchmarks — Litestar's custom ASGI router avoids Starlette overhead
- First-class dependency injection (not overloading `Depends` like FastAPI) — cleaner separation of concerns
- Native DTO (Data Transfer Object) layer — better control over serialization without manual `response_model` wrangling
- Class-based controllers — natural fit for RESTful spec CRUD operations
- Active maintenance with strong release cadence

### Negative

- Smaller community than FastAPI — fewer tutorials, Stack Overflow answers, and third-party integrations
- Team familiarity is lower — FastAPI is more widely known
- Some middleware/plugins built for FastAPI (e.g., certain auth libraries) won't work directly

### Neutral

- Both produce OpenAPI specs — the React frontend can use generated TypeScript types from either
- Migration from Litestar to FastAPI (or vice versa) is straightforward — the JSON API contract stays the same

## References

- Litestar docs: https://docs.litestar.dev
- Litestar benchmarks: https://docs.litestar.dev/latest/benchmarks
