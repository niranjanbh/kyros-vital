# Project context

This is the `kyros-backend` repo — the Python FastAPI backend that serves both the Vital wellness app (Phase 1) and the Kyros clinic platform (Phase 2).

## Required reading before any task

The full build specification is at `../BUILD-SPEC.md`. Read it before starting work on any prompt. It contains:
- Section 1: Locked architectural decisions (do not deviate)
- Section 2: Tech stack
- Section 3: Database schema
- Section 5: Visual design system (mobile only — ignore for backend work)
- Section 6: Prompt queue — you will be given one prompt at a time from here

## Constraints

- Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, Alembic, Poetry
- Single PostgreSQL database, table prefixes `wn_` for wellness, `kc_` for clinic (Phase 2)
- Async throughout; no sync DB calls
- Strict mypy, ruff for lint+format
- All inputs validated via Pydantic schemas, no raw dicts crossing route boundaries
- Audit logging on every mutating endpoint via middleware
- `X-Device-Id` header for guest auth in Phase 1 (no JWT until Phase 1.5)
