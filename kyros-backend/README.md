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

## Demo data

Three realistic demo users can be seeded into any non-production database:

```bash
# Seed all three users (wipes previous demo data first)
poetry run python -m scripts.seed_demo

# Seed only one user
poetry run python -m scripts.seed_demo --only priya
poetry run python -m scripts.seed_demo --only rajesh
poetry run python -m scripts.seed_demo --only anjali

# Dry run — prints what would be seeded, writes nothing
poetry run python -m scripts.seed_demo --dry-run
```

**Priya** (42 F, hypothyroid + early PCOS) — 180 days of data. Four tracked items: Levothyroxine 75mcg (95% adherence), Metformin 500mg twice daily (morning 88%, evening 72%), Myo-Inositol 2g (85%), and daily hydration. Weight trends from 78.4 kg → 74.1 kg over 6 months. Four lab reports tracing a TSH story arc from 8.2 mIU/L (high) down to 2.8 mIU/L (normal), with Vitamin D and HbA1c also normalising.

**Rajesh** (58 M, hypertension + T2D) — 240 days of data. Five tracked items: Amlodipine (91%), Telmisartan (88%), Metformin 1g morning/evening (84%/65%), Atorvastatin (65%), and daily hydration. A stress week at day −120 to −113 drops all adherence to 25% and spikes BP to 158–168 mmHg systolic; the next 30 days show gradual recovery. HbA1c improves from 8.4% → 7.2% across five lab reports.

**Anjali** (29 F, fitness-focused) — 21 days of sparse data. Three tracked items: daily hydration (71%), Multivitamin (90%, started day −10), and Strength Training Mon/Wed/Fri (80%). Three weight measurements and one normal panel.

**Idempotency** — the script identifies its own rows via `device_id LIKE 'demo-seed-%'` and deletes them before re-seeding. Running it twice produces identical row counts.

**Safety guards** — the script refuses to run if `ENV=production` or if the database contains more than 50 non-demo users (guarding against pointing at the wrong database by mistake).

## Architecture decisions

See `../BUILD-SPEC.md` — Section 1 (locked decisions) governs everything in this repo.
