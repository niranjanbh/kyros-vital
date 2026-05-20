# kyros-backend

FastAPI backend serving the Vital wellness app (Phase 1) and Kyros clinic platform (Phase 2).

## Quick start

```bash
cp .env.example .env
docker compose up -d postgres redis
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Commands

```bash
# Lint + format
poetry run ruff check . && poetry run ruff format .

# Type check
poetry run mypy app/

# Tests
poetry run pytest

# Generate OpenAPI schema (commit this to repo for mobile typegen)
python -m app.cli export-openapi --output openapi.json

# Seed database
python -m app.cli seed
```

## Project structure

```
app/
  core/        # Cross-cutting: auth, audit, storage, rate limiting, logging, exceptions
  shared/      # Shared models + routes: users, audit_log, /health
  wellness/    # Phase 1 domain (tracked items, reminders, logs, measurements, lab reports)
  clinic/      # Phase 2 domain (empty placeholder)
alembic/       # Database migrations
tests/
scripts/       # seed.py
```

## Architecture decisions

See `../BUILD-SPEC.md` — Section 1 (locked decisions) governs everything in this repo.
