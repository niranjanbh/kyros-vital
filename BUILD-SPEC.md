# Wellness App — Phase 1 Build Spec (v3: FastAPI + Expo)

One Python backend (`kyros-backend`) serves both the Vital wellness app (Phase 1) and the Kyros clinic platform (Phase 2). One Expo mobile app (`vital-mobile`) consumes typed API contracts. Everything in this file is locked — no freelancing on stack, schema, or patterns.

**How to use this file:** Read sections 1–5 for locked decisions and schema. Section 6 is the backend prompt queue (P0–P7), section 7 is the design generation step, section 8 is the mobile prompt queue (P8–P15). Run one prompt at a time in Claude Code, in order, inside the correct repo directory. Do not parallelize.

---

## 0. Developer environment setup

One-time setup on a fresh Mac. Skip steps already done.

### Required tools

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | 29.x+ | `brew install --cask docker` then open Docker from Applications |
| Python | 3.12.x | `brew install python@3.12` |
| Poetry | 2.x+ | `curl -sSL https://install.python-poetry.org \| python3.12 -` |
| Node.js | 20 LTS+ | `brew install node` |
| pnpm | 9+ | `npm install -g pnpm` |
| Claude Code | latest | `npm install -g @anthropic-ai/claude-code` |

After installing Poetry, add it to your shell PATH permanently:
```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
poetry --version   # should print Poetry (version 2.x.x)
```

### Workspace layout

All work lives under `~/Code/vital/`. The two repos sit as siblings — never nest one inside the other.

```
~/Code/vital/
  BUILD-SPEC.md         ← this file
  kyros-backend/        ← Python FastAPI backend (git repo)
  vital-mobile/         ← Expo React Native app (git repo)
  design-refs/          ← screenshots and mockups used by mobile prompts
    today-screen.png    ← generated in section 7 before P8
```

Create the directories once:
```sh
mkdir -p ~/Code/vital/kyros-backend ~/Code/vital/vital-mobile ~/Code/vital/design-refs
```

### Running backend prompts (P0–P7)

Open `~/Code/vital/kyros-backend` in your IDE. Launch a terminal inside it, then run:
```sh
claude
```
Paste each prompt from section 6 in order, wait for it to finish, review the output, then paste the next.

### Running mobile prompts (P8–P15)

Open `~/Code/vital/vital-mobile` in your IDE. Same pattern:
```sh
claude
```
Paste each prompt from section 8 in order.

### First boot (after P0 completes)

```sh
cd ~/Code/vital/kyros-backend
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, SIGNING_SECRET, ADMIN_PASSWORD_HASH
docker compose up -d postgres redis
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
# API is live at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### Verify everything works

```sh
docker --version          # Docker version 29.x.x
python3.12 --version      # Python 3.12.x
poetry --version          # Poetry (version 2.x.x)
docker info | grep Server # should not say "daemon not running"
```

If Docker daemon is not running, open Docker Desktop from your Applications folder and wait for the whale icon in the menu bar.

---

## 1. Locked architectural decisions

1. **One backend, two domains.** A single FastAPI app (`kyros-backend`) serves both `/v1/wellness/*` (Phase 1) and `/v1/clinic/*` (Phase 2). Same Postgres database, separate table prefixes (`wn_*`, `kc_*`), shared `users` and `audit_log` tables. No microservices, no separate repos.

2. **One schema, three sources.** Every domain table carries a `source` field. Phase 1 writes `source = 'manual'`. Phase 2 adds `source = 'kyros'`. Phase 3 adds `source = 'ai_extracted'`. No new tables in later phases.

3. **The reminder record describes *what*, not *how*.** `channels: ['in_app']` in Phase 1. Phase 2 adds `['whatsapp']`. Phase 3 adds `['voice_call']`. Same schema, dispatcher learns new channels.

4. **Recurrence as a rule, not enumerated rows.** One reminder covers "8am and 8pm every day" via a JSON schedule. `expand_schedule(rule, from_dt, to_dt)` is the single source of truth and lives in Pydantic.

5. **Adherence is first-class.** Every fire can be answered Taken/Skipped/Snoozed → `log_entries`. `fire_key = "{reminder_id}:{fire_at_iso}"` is unique at the DB level — retries can't double-log.

6. **Tracked items ≠ reminders.** Medication = thing with metadata. Reminders = scheduled nudges *about* that thing. One thing, many reminders.

7. **Vitals and lab reports are separate from reminders.** Different data shape, different query patterns. Don't unify.

8. **Soft delete only.** `status='discontinued'`, never `DROP`. Patients and Kyros doctors will ask "what was the dose three months ago."

9. **Guest mode in Phase 1.** No OTP, no login. `X-Device-Id` header identifies the user; the API finds-or-creates a `users` row on first hit. Name, age, and gender are collected during onboarding (mobile) and PATCHed via `/v1/users/me`. OTP arrives in Phase 1.5 with the "back up your data" upgrade prompt.

10. **Online-first, not offline-first.** App talks to the backend on every action. Offline sync is Phase 1.5 — a real 2-week project on its own.

11. **Single EC2 box in Phase 1.** docker-compose with FastAPI + Postgres 16 + Redis on one t3.small in ap-south-1. Migrate to managed services (RDS, ElastiCache, ECS Fargate) only when MRR justifies it.

12. **The mobile app is its own repo.** `vital-mobile` (Expo) is a separate git repo from `kyros-backend`. They share types via committed `openapi.json` consumed by `openapi-typescript`. Independent deploy cycles.

---

## 2. Tech stack (locked)

### Backend — `kyros-backend`

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.12** | Matches Kyros, your strength |
| Framework | **FastAPI 0.115+** | Async, auto OpenAPI for mobile typegen |
| ORM | **SQLAlchemy 2.0 async** | Typed `Mapped[]` style |
| Validation | **Pydantic v2** | Discriminated unions for schedules |
| Migrations | **Alembic** | Doubles as DPDP audit evidence |
| Server | **Uvicorn (dev) + Gunicorn (prod)** | Standard |
| Background jobs | **Celery 5.4 + Redis** | Phase 1: delayed lab-OCR placeholder; Phase 2: WhatsApp dispatch |
| Logging | **structlog** | JSON logs with request_id |
| Linting | **ruff** | Replaces black + isort + flake8 |
| Type checking | **mypy strict** | |
| Tests | **pytest + pytest-asyncio** | |
| Dep mgmt | **Poetry** | |

### Mobile — `vital-mobile`

| Layer | Choice | Notes |
|---|---|---|
| Framework | **Expo (React Native) + TypeScript** | Cross-platform |
| Routing | **expo-router** | File-based |
| Server state | **TanStack Query v5** | |
| Forms | **react-hook-form + zod** | |
| API types | **openapi-typescript** | Generated from backend `openapi.json`, committed to repo |
| Charts | **Victory Native XL + react-native-skia** | |
| Notifications | **expo-notifications** | Local in Phase 1, push later |
| Icons | **lucide-react-native** | Outline only, 1.5 px stroke |
| Fonts | **Fraunces + Geist Sans + Geist Mono** | via expo-font |

### Phase 1 infrastructure (~₹3,000–5,000/month until ~500 active users)

| Component | Choice | Approx ₹/month |
|---|---|---|
| Compute + DB + cache | EC2 t3.small ap-south-1, docker-compose: FastAPI + Postgres 16 + Redis 7 | ~₹1,500 |
| TLS | Caddy reverse proxy (auto Let's Encrypt) | free |
| Backups | pg_dump cron → S3, daily, 30-day retention | ~₹100 |
| Static + DNS | Cloudflare free tier | free |
| Push notifications | Expo free tier (local only Phase 1) | free |
| Object storage | Cloudflare R2 for non-clinical; S3 ap-south-1 for lab reports | ~₹500 |
| Error tracking | Sentry free tier | free |
| Uptime | Better Stack free tier | free |
| Domain | | ~₹100 |

### Phase 2 migration (when MRR > ₹50K/month)

Lift-and-shift to ECS Fargate + RDS Multi-AZ + ElastiCache. The docker-compose definitions translate directly to ECS task definitions. One-day migration, no code changes.

---

## 3. Database schema (PostgreSQL 16)

Drop into Alembic via Prompt P1.

```sql
-- ─────────────────────────────────────────────
-- Shared tables (used by wellness + clinic)
-- ─────────────────────────────────────────────

CREATE TABLE users (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id         TEXT,
  name              TEXT,                          -- set during onboarding PATCH /me
  age               SMALLINT,                      -- set during onboarding PATCH /me
  gender            TEXT,                          -- 'male' | 'female' | 'other' | 'prefer_not_to_say'
  email             TEXT UNIQUE,
  phone             TEXT,
  kyros_patient_id  TEXT,
  role              TEXT NOT NULL DEFAULT 'user',  -- 'user' | 'superadmin'
  subscription_tier TEXT NOT NULL DEFAULT 'free',
  timezone          TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_device_id ON users(device_id) WHERE device_id IS NOT NULL;

CREATE TABLE audit_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
  actor_type    TEXT NOT NULL,   -- 'user' | 'system' | 'doctor' | 'admin'
  action        TEXT NOT NULL,
  resource_type TEXT,
  resource_id   UUID,
  payload       JSONB,
  ip_address    TEXT,
  user_agent    TEXT,
  occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_user_time ON audit_log(user_id, occurred_at DESC);

-- ─────────────────────────────────────────────
-- Wellness domain (prefix wn_)
-- ─────────────────────────────────────────────

CREATE TABLE wn_tracked_items (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category    TEXT NOT NULL,   -- 'medication'|'water'|'meal'|'workout'|'vital_check'|'custom'
  name        TEXT NOT NULL,
  metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
  status      TEXT NOT NULL DEFAULT 'active',   -- 'active'|'paused'|'discontinued'
  start_date  DATE NOT NULL,
  end_date    DATE,
  source      TEXT NOT NULL DEFAULT 'manual',
  source_ref  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_items_user_status   ON wn_tracked_items(user_id, status);
CREATE INDEX idx_wn_items_category      ON wn_tracked_items(user_id, category);

CREATE TABLE wn_reminders (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tracked_item_id  UUID NOT NULL REFERENCES wn_tracked_items(id) ON DELETE CASCADE,
  schedule         JSONB NOT NULL,
  message_template TEXT NOT NULL,
  channels         TEXT[] NOT NULL DEFAULT ARRAY['in_app'],
  active           BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_reminders_active ON wn_reminders(active) WHERE active = true;

CREATE TABLE wn_log_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tracked_item_id UUID NOT NULL REFERENCES wn_tracked_items(id) ON DELETE CASCADE,
  reminder_id     UUID REFERENCES wn_reminders(id) ON DELETE SET NULL,
  fire_key        TEXT,
  action          TEXT NOT NULL,   -- 'taken'|'skipped'|'snoozed'|'logged_value'|'acknowledged'
  value           JSONB NOT NULL DEFAULT '{}'::jsonb,
  note            TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL,
  source          TEXT NOT NULL DEFAULT 'manual',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uniq_wn_log_fire_key ON wn_log_entries(fire_key) WHERE fire_key IS NOT NULL;
CREATE INDEX idx_wn_log_user_time       ON wn_log_entries(user_id, occurred_at DESC);

CREATE TABLE wn_measurements (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type            TEXT NOT NULL,   -- see MeasurementType in section 2 schemas
  value           NUMERIC NOT NULL,
  unit            TEXT NOT NULL,
  measured_at     TIMESTAMPTZ NOT NULL,
  reference_range JSONB,
  source          TEXT NOT NULL DEFAULT 'manual',
  source_ref      TEXT,
  note            TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_measurements_user_type_time ON wn_measurements(user_id, type, measured_at DESC);

CREATE TABLE wn_lab_reports (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_date DATE NOT NULL,
  lab_name    TEXT,
  file_url    TEXT,
  file_mime   TEXT,
  parsed      JSONB NOT NULL DEFAULT '{}'::jsonb,
  source      TEXT NOT NULL DEFAULT 'manual',
  source_ref  TEXT,
  note        TEXT,
  status      TEXT NOT NULL DEFAULT 'active',   -- 'active'|'deleted'
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_lab_reports_user_date ON wn_lab_reports(user_id, report_date DESC);

-- ─────────────────────────────────────────────
-- Clinic domain (prefix kc_) — Phase 2 routes, created now for admin panel
-- ─────────────────────────────────────────────

CREATE TABLE kc_consultations (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id              UUID REFERENCES users(id) ON DELETE SET NULL,
  patient_name         TEXT NOT NULL,
  patient_phone        TEXT NOT NULL,
  patient_email        TEXT,
  condition_category   TEXT,
  preferred_slot       TIMESTAMPTZ,
  status               TEXT NOT NULL DEFAULT 'requested',
                       -- 'requested'|'scheduled'|'completed'|'cancelled'|'no_show'
  meeting_link         TEXT,
  meeting_provider     TEXT,   -- 'zoom'|'meet'|null
  scheduled_at         TIMESTAMPTZ,
  completed_at         TIMESTAMPTZ,
  fee_paid_paise       INTEGER,
  razorpay_payment_id  TEXT,
  source               TEXT NOT NULL DEFAULT 'web',   -- 'web'|'admin'|'whatsapp'
  notes                TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kc_consult_status ON kc_consultations(status, preferred_slot);
CREATE INDEX idx_kc_consult_user   ON kc_consultations(user_id);
CREATE INDEX idx_kc_consult_phone  ON kc_consultations(patient_phone);
```

### Reminder schedule JSON shapes

**Recurring** (medications, meals, workouts):
```json
{
  "type": "recurring",
  "times": ["08:00", "20:00"],
  "days_of_week": ["mon","tue","wed","thu","fri","sat","sun"],
  "start_date": "2026-05-20",
  "end_date": null,
  "timezone": "Asia/Kolkata"
}
```

**Interval** (water):
```json
{
  "type": "interval",
  "interval_minutes": 120,
  "active_window": { "start": "08:00", "end": "22:00" },
  "days_of_week": ["mon","tue","wed","thu","fri","sat","sun"],
  "timezone": "Asia/Kolkata"
}
```

`expand_schedule(schedule, from_dt, to_dt)` lives in `app/wellness/schemas/schedule.py`, uses `zoneinfo` (stdlib, DST-safe), returns timezone-aware datetimes.

---

## 4. Phase 2/3 hooks (no rewrites needed)

- `users.kyros_patient_id` — present from day one.
- `users.role` — defaults to `'user'`; `'superadmin'` unlocks admin panel.
- `source` and `source_ref` on every domain table — populated as `'manual'` in Phase 1.
- `reminders.channels` as an array — room for `'whatsapp'`, `'voice_call'`, `'sms'`.
- `metadata` and `parsed` as JSONB — Phase 3 AI extraction populates the same shapes humans fill manually.
- `IStorageAdapter` interface — Phase 1 `LocalDiskStorage`, Phase 2 swaps to S3.
- The `clinic/` folder is empty in Phase 1 (aside from `kc_consultations`); Phase 2 fills it with consultation, prescription, and lab-order routes.

---

## 5. Visual design system

Aesthetic direction: **editorial clinical** — refined, restrained, warm. Like a premium medical journal, not a wellness app from a Lovable template.

### Type stack (open source, loaded via expo-font from Google Fonts CDN)

- **Display + large numerals:** Fraunces (variable serif, optical-size aware, tight leading 1.1)
- **Body + UI:** Geist Sans (regular 400, medium 500, semibold 600)
- **Mono / tabular:** Geist Mono (regular 400, medium 500)
- **Section labels:** Geist Sans, uppercase, 11px, letter-spacing 0.08em, `#8C8C8C`

Avoid Inter, Roboto, SF Pro, generic system fonts.

### Colour tokens

```ts
export const tokens = {
  // Surfaces & text
  bone:        '#F7F4ED',   // primary background (warm, slightly darker than pure cream)
  paper:       '#FFFFFF',   // card surface
  ink:         '#1A1A1A',   // primary text
  slate:       '#5C5C5C',   // secondary text
  mist:        '#8C8C8C',   // tertiary, labels
  hairline:    '#E8E3D8',   // 1px borders
  divider:     '#F0EBE0',   // subtle dividers

  // Accent
  tealDeep:    '#2D5F5D',   // global accent — used sparingly

  // Status
  positive:    '#3F6B4E',   // muted forest green
  warning:     '#B07A1F',   // muted amber
  critical:    '#8B2C1F',   // muted brick
  missed:      '#B85C3C',   // muted terracotta

  // State washes (card backgrounds for logged states)
  takenWash:   '#EAF0EC',   // ~6% saturation forest tint — do NOT brighten
  snoozedWash: '#FBF3E3',   // ~6% saturation amber tint — do NOT brighten

  // Category accents (used on icons, left-edge strips, section labels)
  categoryMedication: '#4A5D7E',   // slate navy
  categoryHydration:  '#5B8A8F',   // muted seafoam
  categoryActivity:   '#8B5A3C',   // warm clay
  categoryNutrition:  '#7A6F4D',   // olive ochre
  categoryVitals:     '#6B4E71',   // dusky plum
  categoryCustom:     '#6B6F4D',   // sage

  // Charts
  chartLine:   '#1A1A1A',   // charts default to ink, not colour
} as const;
```

### Layout grammar

- 8-pt grid: 4 / 8 / 12 / 16 / 24 / 32 / 48
- Hairline borders, not shadows. One subtle shadow on Today cards only.
- Card radius 8px, button radius 10px. No pill shapes, no blobs.
- 32px between sections, 12–14px between timeline items, 20px horizontal padding.

### Numerical typography

- Big numbers (weight, BP, HbA1c) in Fraunces 36–64px, tight leading.
- Unit (`kg`, `mmHg`, `%`) in Geist Sans, smaller, `slate`.
- Trend indicators are typographic, not emoji: `▲ ▼ —` in `positive` / `critical` / `slate`.

### Iconography

lucide-react-native, outline only, 1.5px stroke, never filled.

### Banned by default

Purple/pink gradients, glassmorphism, neon cyan, 3D icons, emoji in UI chrome, Tailwind defaults like `bg-blue-500`.

---

## 6. Prompt queue

Two repos. Run backend prompts (P0–P7) in `kyros-backend/`, then mobile prompts (P8–P15) in `vital-mobile/`. Do not parallelize — each prompt builds on the previous.

---

### P0 — Backend repo scaffold (`kyros-backend`)

```
Initialize a new Python project at the current directory for the Kyros backend — a FastAPI application that will serve both the Vital wellness app (Phase 1) and the Kyros clinic platform (Phase 2). Single codebase, separate domain modules.

Create this directory structure:

  app/
    __init__.py
    main.py                      # FastAPI factory, mounts routers
    config.py                    # Pydantic Settings, loads from env
    database.py                  # async SQLAlchemy engine, sessionmaker, Base

    core/                        # Cross-cutting utilities, used by all domains
      __init__.py
      auth.py                    # get_current_user dependency (guest mode in Phase 1)
      audit.py                   # Audit middleware → audit_log table (DPDP)
      storage.py                 # IStorageAdapter protocol + LocalDiskStorage
      rate_limit.py              # slowapi setup
      logging.py                 # structlog config with request_id contextvar
      exceptions.py              # Custom exceptions + handlers

    shared/                      # Tables/routes shared across wellness + clinic
      __init__.py
      models/__init__.py         # users, audit_log SQLAlchemy models
      schemas/__init__.py        # Pydantic schemas for users
      routes/__init__.py         # /health, /v1/users

    wellness/                    # Phase 1 domain (this work)
      __init__.py
      models/__init__.py
      schemas/__init__.py
      routes/__init__.py
      services/__init__.py

    clinic/                      # Phase 2 domain (empty placeholder)
      __init__.py

    admin/                       # Server-rendered admin panel (P6)
      __init__.py

    cli.py                       # typer CLI: export-openapi, seed

  alembic/
    versions/
    env.py                       # configured for async engine, autogenerate
    script.py.mako
  alembic.ini

  tests/
    conftest.py
    core/__init__.py
    shared/__init__.py
    wellness/__init__.py
    admin/__init__.py
    scripts/__init__.py

  scripts/
    seed.py
    seed_demo.py                 # created in P7

  pyproject.toml                 # Poetry
  poetry.lock
  .env.example
  .gitignore
  README.md
  Dockerfile                     # multi-stage, slim base, non-root user
  docker-compose.yml             # postgres 16, redis 7, api with hot reload
  .dockerignore
  Caddyfile                      # reverse proxy config for Phase 1 EC2 deploy
  .github/workflows/
    test.yml                     # pytest + ruff + mypy on PR
    deploy.yml                   # ssh + docker compose pull && up on push to main

Python and package versions:
- Python 3.12
- FastAPI 0.115+
- SQLAlchemy 2.0 async
- Alembic 1.13+
- Pydantic v2
- structlog 24.x
- httpx 0.27+
- slowapi
- Jinja2 (for admin panel in P6)
- passlib[bcrypt] (for admin auth in P6)
- typer (for CLI)
- pytest + pytest-asyncio + pytest-cov

Tooling:
- Poetry for dependency management
- ruff for lint + format (line length 100, target py312)
- mypy strict mode
- pre-commit hooks for ruff + mypy

docker-compose.yml must bring up postgres 16, redis 7, and the API on localhost:8000 with hot reload via `uvicorn --reload`.

.env.example must contain:
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kyros
  REDIS_URL=redis://localhost:6379/0
  STORAGE_DIR=./storage
  STORAGE_BACKEND=local
  SIGNING_SECRET=changeme
  LOG_LEVEL=INFO
  ENV=development
  ADMIN_USERNAME=admin
  ADMIN_PASSWORD_HASH=<bcrypt hash — generate with passlib>
  SENTRY_DASHBOARD_URL=https://sentry.io/...
  UPTIME_DASHBOARD_URL=https://uptime.betterstack.com/...
  ADMIN_SESSION_TIMEOUT_MINUTES=60

Do NOT add any wellness routes, models, or domain logic yet. Only scaffolding with empty __init__.py files everywhere.

After scaffolding, print the directory tree and boot commands:
  cp .env.example .env
  docker compose up -d postgres redis
  poetry install
  poetry run alembic upgrade head   (no-op until P1)
  poetry run uvicorn app.main:app --reload
```

---

### P1 — SQLAlchemy models + Alembic migrations

```
In app/shared/models/ and app/wellness/models/, define SQLAlchemy 2.0 models for all Phase 1 tables from the build spec schema (section 3). Also include the kc_consultations table.

Shared models (app/shared/models/):

  users.py — class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('gen_random_uuid()'))
    device_id: Mapped[str | None] = mapped_column(Text, index=True)
    name: Mapped[str | None] = mapped_column(Text)
    age: Mapped[int | None] = mapped_column(SmallInteger)
    gender: Mapped[str | None] = mapped_column(Text)   # 'male'|'female'|'other'|'prefer_not_to_say'
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    phone: Mapped[str | None] = mapped_column(Text)
    kyros_patient_id: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, server_default=text("'user'"))
    subscription_tier: Mapped[str] = mapped_column(Text, server_default=text("'free'"))
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'Asia/Kolkata'"))
    created_at, updated_at: Mapped[datetime] (TIMESTAMPTZ, server defaults)

  audit_log.py — class AuditLog(Base): per schema section 3.

Wellness models (app/wellness/models/), one file each:

  tracked_item.py — class TrackedItem(Base):
    __tablename__ = 'wn_tracked_items'
    All fields per schema. user_id FK ON DELETE CASCADE.
    Index('idx_wn_items_user_status', 'user_id', 'status')
    Relationship: reminders = relationship('Reminder', back_populates='tracked_item', cascade='all, delete-orphan')

  reminder.py — class Reminder(Base):
    __tablename__ = 'wn_reminders'
    schedule: Mapped[dict] = mapped_column(JSONB)
    channels: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("ARRAY['in_app']"))
    active: Mapped[bool] default true
    Relationship: tracked_item = relationship('TrackedItem', back_populates='reminders')

  log_entry.py — class LogEntry(Base):
    __tablename__ = 'wn_log_entries'
    Partial unique index: fire_key IS NOT NULL
    reminder_id FK ON DELETE SET NULL

  measurement.py — class Measurement(Base):
    __tablename__ = 'wn_measurements'
    value: Mapped[Decimal] = mapped_column(Numeric)
    Index on (user_id, type, measured_at DESC)

  lab_report.py — class LabReport(Base):
    __tablename__ = 'wn_lab_reports'
    parsed: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

Clinic models (app/clinic/models/):

  consultation.py — class Consultation(Base):
    __tablename__ = 'kc_consultations'
    All fields per schema section 3. user_id FK ON DELETE SET NULL.
    Indexes as specified.

Requirements:
- All models inherit from Base in app/database.py
- All UUID PKs use server_default=text('gen_random_uuid()')
- All TIMESTAMPTZ use server_default=text('now()'); updated_at also server_onupdate
- All FK cascades exactly as specified in the schema
- All indexes as Index() at module level
- Use Mapped[] throughout (SQLAlchemy 2.0 typed style)
- Add __repr__ to each model
- Export all models from their package __init__.py for Alembic autogenerate
- alembic/env.py imports all models so autogenerate sees them

After writing models:
1. Run `alembic revision --autogenerate -m "initial schema"`
2. Inspect the generated SQL — must match section 3 of the build spec
3. Run `alembic upgrade head` against docker-compose postgres
4. Write scripts/seed.py that creates: 1 guest user (name="Test User", age=30, gender="prefer_not_to_say"), 1 medication tracked item with a recurring twice-daily reminder, 1 water tracked item with a 2-hour interval reminder, 1 workout tracked item with a 3-day-a-week reminder

Tests in tests/wellness/test_models.py:
- Save and fetch each model
- Cascade delete: deleting User deletes wn_tracked_items → wn_reminders → wn_log_entries
- Reminder deletion sets log_entry.reminder_id to NULL (not cascade delete)
- Unique fire_key: inserting the same fire_key twice raises IntegrityError

After completion: print the generated migration SQL and the seed script output.
```

---

### P2 — Pydantic schemas + core utilities

```
Build the Pydantic schemas and core utilities.

In app/wellness/schemas/, one file each:

schedule.py:
  RecurringSchedule(BaseModel):
    type: Literal['recurring']
    times: list[str]              # validator: each matches r'^([01]\d|2[0-3]):[0-5]\d$'
    days_of_week: list[Literal['mon','tue','wed','thu','fri','sat','sun']]  # non-empty
    start_date: date
    end_date: date | None = None
    timezone: str                 # validator: valid IANA timezone via zoneinfo

  IntervalSchedule(BaseModel):
    type: Literal['interval']
    interval_minutes: int         # gt=0, le=1440
    active_window: dict           # {'start': 'HH:MM', 'end': 'HH:MM'}, end > start
    days_of_week: list[Literal['mon','tue','wed','thu','fri','sat','sun']]
    timezone: str

  Schedule = Annotated[Union[RecurringSchedule, IntervalSchedule], Field(discriminator='type')]

  def expand_schedule(schedule: Schedule, from_dt: datetime, to_dt: datetime) -> list[datetime]:
    """
    Return timezone-aware datetimes when the reminder fires, within [from_dt, to_dt).
    Recurring: iterate each date, each time, filter by days_of_week.
    Interval: iterate from from_dt by interval_minutes, filter by active_window and days_of_week.
    Uses zoneinfo for DST safety. Returns sorted ascending.
    """

tracked_item.py:
  Category = Literal['medication','water','meal','workout','vital_check','custom']
  Source = Literal['manual','kyros','ai_extracted']
  Status = Literal['active','paused','discontinued']
  Gender = Literal['male','female','other','prefer_not_to_say']

  MedicationMeta(BaseModel): drug_name, dosage, form: Literal['tablet','capsule','syrup','injection','other'], with_food: bool = False, instructions: str | None = None
  WaterMeta(BaseModel): daily_target_ml: int, glass_size_ml: int = 250
  WorkoutMeta(BaseModel): workout_type, duration_minutes: int, location: str | None = None
  MealMeta(BaseModel): meal_name, notes: str | None = None
  CustomMeta(BaseModel): title, notes: str | None = None

  TrackedItemBase(BaseModel): category, name, metadata: dict
  TrackedItemRead(TrackedItemBase): id, user_id, status, start_date, end_date, source, source_ref, created_at, updated_at, reminders: list[ReminderRead]
  TrackedItemCreate(BaseModel): category, name, metadata, start_date, end_date | None
  TrackedItemUpdate(BaseModel): all fields optional

reminder.py:
  ReminderRead: id, tracked_item_id, schedule, message_template, channels, active, created_at, updated_at
  ReminderCreate: schedule, message_template, channels: list[str] = ['in_app']
  ReminderUpdate: all optional

  UpcomingFire(BaseModel):
    reminder_id: UUID
    tracked_item_id: UUID
    fire_at: datetime   # tz-aware
    fire_key: str       # f'{reminder_id}:{fire_at.isoformat()}'
    payload: dict       # {title, body, category, actions: list[str]}

log_entry.py:
  LogAction = Literal['taken','skipped','snoozed','logged_value','acknowledged']
  LogEntryRead, LogEntryCreate (fire_key?, reminder_id?, value?, note?, occurred_at)

measurement.py:
  MeasurementType = Literal['weight','bp_systolic','bp_diastolic','heart_rate','fasting_glucose','hba1c','body_temp','steps']
  MeasurementRead, MeasurementCreate, MeasurementUpdate

lab_report.py:
  ParsedTest(BaseModel): name, value: str, unit, ref_low: float | None, ref_high: float | None, flag: Literal['normal','low','high','critical']
  LabReportRead, LabReportCreate, LabReportUpdate

In app/shared/schemas/:

users.py:
  UserRead: id, device_id, name, age, gender, email, phone, kyros_patient_id, role, subscription_tier, timezone, created_at, updated_at
  UserUpdate: name, age, gender, email, timezone — all optional. subscription_tier and role are NOT patchable from this endpoint.

In app/core/:

storage.py:
  class IStorageAdapter(Protocol):
    async def save(content: bytes, key: str, mime_type: str) -> str
    async def read(key: str) -> bytes
    async def delete(key: str) -> None
    async def signed_url(key: str, ttl_seconds: int = 3600) -> str

  class LocalDiskStorage(IStorageAdapter):
    base_dir from STORAGE_DIR env. signed_url returns path with HMAC token (SIGNING_SECRET env).

  def get_storage() -> IStorageAdapter: factory reads STORAGE_BACKEND env.

audit.py:
  Middleware: on every successful POST/PATCH/DELETE, writes an audit_log row.
  Fields: user_id (from request.state.user), actor_type='user', action=request.url.path,
  resource_type extracted from path, resource_id from response body if present, ip_address, user_agent, payload=request body (PII-scrubbed: remove fields named 'password', 'token', 'secret').

auth.py:
  async def get_current_user(request: Request, db: AsyncSession) -> User:
    Read X-Device-Id header (required, raise 401 if missing).
    Validate format: 16–64 chars, alphanumeric + dashes.
    Query users by device_id. If exists, return.
    If not: INSERT with ON CONFLICT (device_id) DO NOTHING RETURNING, then re-fetch.
    Store user on request.state for audit middleware.

rate_limit.py:
  slowapi Limiter keyed on request.state.user.id if present else IP.
  Default limit: 60/minute per user. Lab-report POST: 10/minute.

logging.py:
  structlog config: JSON in prod, console-pretty in dev.
  request_id (uuid4) contextvar populated by middleware.

exceptions.py:
  NotFoundError, ForbiddenError, ValidationError, RateLimitError, ConflictError.
  Handlers return: { error: { code, message, request_id, details? } }

Tests:
  tests/wellness/schemas/test_schedule.py:
    - expand_schedule recurring 8am+8pm IST over 48h → exactly 4 events
    - expand_schedule interval 2h 8–22 weekdays over 24h on Monday → ~7–8 events
    - expand_schedule across Asia/Kolkata day boundary
    - expand_schedule across US/Eastern DST boundary → no missing/duplicate fires
    - end_date respected
    - empty days_of_week → ValidationError on construction

  tests/core/test_storage.py:
    - LocalDiskStorage save → read → delete roundtrip
    - signed_url has valid HMAC, expires after TTL

  tests/core/test_auth.py:
    - Missing X-Device-Id → 401
    - New device_id → creates user
    - Same device_id twice → returns same user (no duplicate)

  tests/core/test_audit.py:
    - POST request writes one audit_log row with correct fields

After completion: pytest with coverage, target ≥80% on core/ and schemas/.
```

---

### P3 — API foundations + users endpoint + OpenAPI export

```
Wire up the FastAPI app, shared routes, and export the OpenAPI schema.

app/main.py:
  def create_app() -> FastAPI:
    app = FastAPI(
      title='Kyros Backend',
      version='0.1.0',
      docs_url='/docs' if config.ENV != 'production' else None,
    )
    Register middleware in order: request_id → logging → CORS → audit → rate_limit
    Register exception handlers from core/exceptions
    Mount routers:
      app.shared.routes.health    → /health
      app.shared.routes.users     → /v1/users
      # wellness and admin mounts come in P4–P6
    Customize OpenAPI to include X-Device-Id as a required global header

app/shared/routes/health.py:
  GET /health → { status, version, env, db: 'reachable'|'unreachable', storage: 'reachable'|'unreachable' }
  Pings DB (SELECT 1) and storage.signed_url('healthcheck').

app/shared/routes/users.py:
  router = APIRouter(prefix='/v1/users', tags=['Users'])

  POST /guest
    No auth — requires X-Device-Id header.
    Idempotent: returns existing user for that device_id, or creates new one.
    Response: UserRead.

  GET /me
    Depends(get_current_user)
    Response: UserRead.

  PATCH /me
    Depends(get_current_user)
    Body: UserUpdate { name?, age?, email?, gender?, timezone? }
    Returns: UserRead.
    Note: name, age, gender collected during onboarding are sent here. They are optional — users can skip profile setup.

app/cli.py (typer):
  $ python -m app.cli export-openapi --output openapi.json
    Generates and writes OpenAPI schema to disk (consumed by vital-mobile typegen).

  $ python -m app.cli seed
    Runs scripts/seed.py.

Tests:
  tests/conftest.py:
    - Async test client fixture
    - Test DB: fresh schema per test session, drops after
    - Async session with rollback per test
    - Sample User fixture (name="Test User", age=30, gender="prefer_not_to_say")

  tests/shared/test_health.py:
    - GET /health → 200, status='ok', db='reachable'

  tests/shared/test_users.py:
    - POST /v1/users/guest new device_id → 201, user returned
    - POST /v1/users/guest same device_id → 200 (or 201), same user.id
    - GET /v1/users/me valid X-Device-Id → 200
    - GET /v1/users/me missing X-Device-Id → 401
    - PATCH /me with name="Priya", age=42, gender="female" → 200, returned user reflects update
    - PATCH /me with subscription_tier → 422 (field not allowed)

After completion:
  - docker compose up
  - curl http://localhost:8000/health → verify 200
  - curl -X POST -H 'X-Device-Id: test-abc123456789' http://localhost:8000/v1/users/guest → verify user creation
  - curl -X PATCH -H 'X-Device-Id: test-abc123456789' -d '{"name":"Niranjan","age":30,"gender":"male"}' http://localhost:8000/v1/users/me
  - Open http://localhost:8000/docs and verify OpenAPI UI renders
  - python -m app.cli export-openapi --output openapi.json → commit openapi.json
```

---

### P4 — Wellness API: tracked items + reminders + upcoming fires

```
Build the wellness domain routes for tracked items and reminders.

In app/wellness/routes/tracked_items.py:
  router = APIRouter(prefix='/v1/wellness/tracked-items', tags=['Wellness'])
  All endpoints Depends(get_current_user).

  GET    /                       ?category=&status=  → list user's items with embedded reminders
  POST   /                       body: TrackedItemCreate
  GET    /{item_id}              → item with embedded reminders[]
  PATCH  /{item_id}              body: TrackedItemUpdate
  DELETE /{item_id}              → soft delete: status='discontinued', deactivate all child reminders

  GET    /{item_id}/reminders    → list reminders for item
  POST   /{item_id}/reminders    body: ReminderCreate

In app/wellness/routes/reminders.py:
  router = APIRouter(prefix='/v1/wellness/reminders', tags=['Wellness'])

  PATCH  /{reminder_id}          body: ReminderUpdate
  DELETE /{reminder_id}          → active=false (soft delete)

  GET    /upcoming               ?hours=24 (default 24, max 168) → list[UpcomingFire]

In app/wellness/services/upcoming.py:
  async def compute_upcoming(user_id, hours, db) -> list[UpcomingFire]:
    1. Fetch active reminders for user (status='active', reminder.active=true, within date range)
    2. expand_schedule(reminder.schedule, now, now+hours) for each
    3. Build UpcomingFire per fire:
       - fire_key = f'{reminder.id}:{fire_at.isoformat()}'
       - payload.title: 'Medication'|'Hydration'|'Workout'|'Meal'|'Vitals'|'Reminder'
       - payload.body: render message_template with metadata via str.format_map(SafeDict) — missing keys render as the literal key, never crash
       - payload.actions per category:
           medication → ['taken','skipped','snooze_15']
           water      → ['logged_value','skipped','snooze_15']
           meal       → ['taken','skipped','snooze_15']
           workout    → ['taken','skipped','snooze_30']
           vital_check→ ['logged_value','skipped','snooze_15']
           custom     → ['acknowledged','snooze_15']
    4. Return sorted ascending by fire_at.

Mount routers in app/main.py.

Requirements:
- All query filters include user_id = current_user.id; cross-user access returns 404 (not 403, don't leak existence)
- TrackedItemCreate validates metadata against per-category schema
- Soft delete: DELETE on tracked_item sets status='discontinued' AND active=false on all child reminders, in one transaction

Tests in tests/wellness/routes/:
  test_tracked_items.py:
    - Full CRUD lifecycle for medication
    - Cross-user: user A creates, user B GETs → 404
    - Soft delete: status='discontinued', child reminders deactivated, item still readable
    - Invalid metadata → 422 with field-level errors

  test_reminders.py:
    - Create/update/delete reminder
    - Schedule validation: invalid timezone, end before start → 422

  test_upcoming.py:
    - Recurring twice-daily medication → 4 events over 48h
    - Interval water every 2h 8–22 weekdays → ~8 events on weekday, 0 events if all days are excluded
    - Template substitution: {drug_name} replaced from metadata; missing {foo} renders as 'foo'
    - DST boundary US/Eastern → no double-fires, no missing fires
    - Inactive reminder excluded, discontinued tracked_item excluded, cross-user excluded
    - hours=24 returns subset of hours=48

Update openapi.json and commit.

After completion: curl integration test —
  1. Create medication via POST
  2. Create twice-daily reminder
  3. GET /upcoming?hours=48
  4. Verify 4 fire events with correct bodies and actions
```

---

### P5 — Wellness API: logs + measurements + lab reports

```
Build the remaining wellness routes.

In app/wellness/routes/logs.py:
  router = APIRouter(prefix='/v1/wellness/logs', tags=['Wellness'])

  POST /
    Body: LogEntryCreate { tracked_item_id, action, reminder_id?, fire_key?, value?, note?, occurred_at }
    If fire_key provided and log already exists with that fire_key → return existing row HTTP 200 (idempotent).
    Else: insert and return 201.
    Implementation: INSERT ... ON CONFLICT (fire_key) DO NOTHING RETURNING *; if no row returned, re-fetch.

  DELETE /{id}
    Soft-deletes the log entry (sets a deleted_at timestamp or status='deleted').
    Required for the Undo affordance in the mobile app — when user undoes a log action within 8s.
    Returns 204 on success. Returns 404 if not found or not owned by current user.

  GET /
    ?from=&to=&tracked_item_id=&action=
    Cursor-based pagination, default limit 50, max 200, newest first.

In app/wellness/routes/measurements.py:
  router = APIRouter(prefix='/v1/wellness/measurements', tags=['Wellness'])

  POST   /              create
  GET    /              ?type=&from=&to=, paginated newest first
  GET    /{id}          read
  PATCH  /{id}          partial update
  DELETE /{id}          hard delete (user corrections — not adherence history)

In app/wellness/routes/lab_reports.py:
  router = APIRouter(prefix='/v1/wellness/lab-reports', tags=['Wellness'])

  POST /                multipart upload:
    file: UploadFile (max 10 MB; accept image/jpeg, image/png, application/pdf)
    metadata: JSON form field — report_date, lab_name, parsed: list[ParsedTest], note
    Implementation:
      1. Validate size and mime
      2. storage key: f'user-{user.id}/labs/{uuid4()}-{secure_filename(file.filename)}'
      3. await storage.save(content, key, mime_type)
      4. Insert lab_report row
      5. Return LabReportRead with signed URL

  GET    /              list, newest first, paginated
  GET    /{id}          detail with fresh signed URL
  GET    /{id}/file     verify access, return streaming response from storage.read()
  PATCH  /{id}          edit metadata or parsed JSON (NOT the file)
  DELETE /{id}          soft delete: status='deleted', keep file for later cleanup

Mount routers in app/main.py.

Requirements:
- Log entry idempotency: catch IntegrityError race condition (two concurrent POSTs same fire_key), re-query, return existing
- Lab report POST rate-limited 10/min per user
- File access: GET /{id}/file checks lab_report belongs to current_user before storage.read()
- Never call open() or pathlib directly in route code — always through IStorageAdapter
- Soft delete on lab_report does NOT call storage.delete() immediately

Tests in tests/wellness/routes/:
  test_logs.py:
    - POST new fire_key → 201
    - POST same fire_key → 200, same row
    - Race condition simulation: two concurrent POSTs → both return same row, no duplicate
    - DELETE log entry → 204; re-GET upcoming shows card back in pending state
    - Filtering by tracked_item_id, action, date range
    - Cross-user → 404

  test_measurements.py:
    - CRUD lifecycle
    - Type filtering, time-range query

  test_lab_reports.py:
    - Upload PDF → 201, signed URL returned
    - Upload >10 MB → 413; wrong mime → 415
    - GET /{id}/file valid auth → 200, content matches
    - GET /{id}/file other user → 404
    - PATCH parsed JSON → GET reflects change
    - DELETE → status='deleted', GET → 404

Update openapi.json and commit.

After completion: full curl integration test —
  1. Create medication and reminder
  2. GET /upcoming, pick first fire
  3. POST /logs action='taken' with fire_key → 201
  4. POST same → 200, same row
  5. DELETE the log entry → 204
  6. GET /upcoming → same fire reappears (no longer logged)
  7. POST /measurements weight=72.4
  8. POST /lab-reports upload a sample PDF
  9. GET /lab-reports/{id}/file → file streams back
```

---

### P6 — Admin panel (`/admin`)

```
Extend kyros-backend with a server-rendered HTML admin panel mounted at /admin.

Locked decisions:
- Mount point: /admin/*. Root URL: /admin/.
- Auth: HTTP Basic Auth (FastAPI HTTPBasic). Credentials from ADMIN_USERNAME and ADMIN_PASSWORD_HASH (bcrypt). Failed auth → 401 WWW-Authenticate: Basic.
- Rendering: Jinja2 templates in app/admin/templates/. Static assets in app/admin/static/.
- Read-mostly: only write actions are (a) mark consultation status, (b) discontinue tracked item, (c) toggle reminder active flag.
- Confirmation pattern: every write action requires typing a specific phrase (e.g. "DISCONTINUE") before POST is accepted. Server validates. No JS confirmations.
- Audit: every admin action (including sensitive GET like user detail, consultation detail) writes audit_log with actor_type='admin'.
- No PHI in structlog: redact payload, metadata, notes, dose, lab_value, result from application logs. Admin UI can show them; structlog must not.
- statement_timeout = 5000ms on all admin DB queries to prevent runaway queries.

Create this structure:
app/admin/
  __init__.py
  auth.py              # HTTPBasic dependency, bcrypt verify
  deps.py              # require_admin() dependency, get_admin_db()
  routes/
    __init__.py
    dashboard.py       # GET /admin/
    users.py           # GET /admin/users, GET /admin/users/{id}
    items.py           # GET /admin/items, POST /admin/items/{id}/discontinue
    reminders.py       # GET /admin/reminders, POST /admin/reminders/{id}/toggle
    consultations.py   # GET /admin/consultations, POST /admin/consultations/{id}/status
    audit.py           # GET /admin/audit
    health.py          # GET /admin/health
  templates/
    base.html
    dashboard.html
    users_list.html
    user_detail.html
    items_list.html
    reminders_list.html
    consultations_list.html
    consultation_detail.html
    audit_log.html
    health.html
    confirm_action.html    # reusable confirmation page
  static/
    admin.css              # ~150 lines, no framework
  services/
    metrics.py             # all dashboard queries, each as a testable function, 30s in-process cache
    audit.py               # write_admin_audit(db, request, action, resource_type, resource_id, payload)

Register admin router in app/main.py AFTER JSON API routers, mounted at /admin. Mount static at /admin/static.

Dashboard (GET /admin/) metrics — computed in services/metrics.py:

  Block 1: Users
    - Total users, active last 7d, active last 30d, new last 7d, users with email set

  Block 2: Tracked items
    - Total by status (active/paused/discontinued)
    - Total by category
    - Created last 7d, discontinued last 7d

  Block 3: Reminders & adherence
    - Total reminders, active reminders
    - Fires expected per day (expand_schedule over next 24h)
    - Last 7d adherence: taken/(taken+skipped+missed)
    - Last 7d missed count (fires with no log within 4h)

  Block 4: Consultations
    - Bookings last 7d, status breakdown, upcoming 48h count, revenue last 30d

  Block 5: System
    - DB connection, Redis connection, last Alembic migration timestamp
    - Disk usage (shutil.disk_usage), Sentry link, Better Stack link

  Block 6: Recent activity — last 20 audit_log rows, link to /admin/audit

List views (pagination: ?page=N&size=50, server-side LIMIT/OFFSET):

  GET /admin/users — id (truncated), device_id/phone, name, age, gender, email, tier, role, created_at, item_count, last_activity_at. Each row links to /admin/users/{id}.

  GET /admin/users/{id} — identity block (id, device_id, name, age, gender, email, phone, timezone, tier, role, created_at), tracked items table, last 30 log entries, last 30 audit entries, linked consultations. View-only.

  GET /admin/items — id, user (link), category, name, status, start_date, source, reminders_count. Filter by status/category. "Discontinue" button → confirmation → POST /admin/items/{id}/discontinue.

  GET /admin/reminders — id, item (link), schedule summary, channels, active. "Pause"/"Resume" → confirmation → POST /admin/reminders/{id}/toggle.

  GET /admin/consultations — id, patient_name, patient_phone, condition_category, status, preferred_slot, fee_paid_paise. Filter by status. Row links to detail.

  GET /admin/consultations/{id} — full detail. Form to update status, meeting_link, meeting_provider, scheduled_at, notes. Submits to POST /admin/consultations/{id}/status (through confirmation page).

  GET /admin/audit — paginated audit_log viewer. Filter by actor_type, action, user_id, date range. Payload as <pre>.

Confirmation page pattern:
  confirm_action.html takes: action_label, action_description, confirmation_phrase, submit_url, cancel_url.
  Handler validates request.form['confirmation'] == confirmation_phrase (case-sensitive).
  Wrong phrase → re-render with error. Correct → perform action, write audit log, redirect with flash.

CLI command:
  poetry run python -m app.admin.cli set-password
    Prompts for password, prints bcrypt hash to stdout. Never writes plaintext to disk.

Styling:
  admin.css ~150 lines. Bone background (#F7F4ED), ink text (#1A1A1A), hairline borders (#E8E3D8).
  Tables: hairline borders, no zebra striping. Buttons: bordered, no shadows. Destructive buttons: #B85C3C border.
  Top nav with current section underlined. No JavaScript. No framework. No icons. Forms submit and reload.

Tests in tests/admin/:
  test_auth.py — 401 no creds, 401 wrong creds, 200 right creds
  test_dashboard.py — all metric functions return correct shape, dashboard renders 200
  test_confirmation.py — wrong phrase rejects and writes no DB change, right phrase commits and writes audit row
  test_audit_redaction.py — structlog output does NOT contain PHI fields after admin views a consultation with notes

Add docs/ADMIN.md covering: how to set password, URL, list of write actions, audit log retention (forever in Phase 1), how to add a second admin in Phase 1.5.

NOT in this prompt:
  ❌ No React/HTMX/Alpine or any client-side framework
  ❌ No SQL console or raw query endpoint
  ❌ No user impersonation (Phase 1.5)
  ❌ No CSV export (Phase 1.5)
  ❌ No charts
  ❌ No role management UI (role column is for future use)
  ❌ No password change UI (CLI only)
  ❌ No delete user action

Acceptance criteria:
  1. curl https://localhost/admin/ → 401 WWW-Authenticate: Basic
  2. Dashboard loads <500ms on t3.small with 1000 seeded users
  3. Discontinuing item via UI: sets status='discontinued', writes audit_log row
  4. Wrong confirmation phrase: inline error, no data mutation
  5. grep for PHI fields in logs after admin session → zero matches
  6. mypy --strict app/admin/ passes
  7. ruff check app/admin/ passes
```

---

### P7 — Demo data seeding script

```
Create a realistic, idempotent demo data seeding script. This exercises every dashboard surface and makes the app look alive during development and demos.

Safety constraints (non-negotiable):
  1. Identifies its own data via device_id prefix 'demo-seed-'. Users are demo-seed-priya, demo-seed-rajesh, demo-seed-anjali.
  2. On start: DELETE CASCADE any users row whose device_id starts with 'demo-seed-'.
  3. Refuses to run if ENV == 'production' → RuntimeError("Refusing to seed demo data into production").
  4. Refuses to run if database has >50 non-demo users → fails fast (wrong DB guard).
  5. Uses app.wellness.services.* where possible. Raw SQLAlchemy session only for batch log entry inserts.
  6. All datetimes timezone-aware (Asia/Kolkata), relative to datetime.now(ZoneInfo("Asia/Kolkata")).
  7. random.seed(42) at top. Byte-identical results on every run.

Architecture:
  scripts/seed_demo.py            # entry point: argparse, runs all three
  scripts/seed/
    __init__.py
    common.py                     # helpers: IST, days_ago(), jittered_time(), weighted_action()
    user_priya.py                 # User A: thyroid + PCOS, 180 days
    user_rajesh.py                # User B: HTN + T2D polypharmacy, 240 days
    user_anjali.py                # User C: fitness, sparse, 21 days

Each user module: async def seed(db: AsyncSession) -> UUID

CLI:
  poetry run python -m scripts.seed_demo                  # seed all three
  poetry run python -m scripts.seed_demo --only priya     # seed one
  poetry run python -m scripts.seed_demo --dry-run        # print plan, no writes

─────────────────────────────────────────────────────────

USER A — Priya, 42, female, hypothyroid + early PCOS (180 days)

Profile: device_id='demo-seed-priya', email='priya.demo@kyros.local', name='Priya', age=42, gender='female', timezone='Asia/Kolkata'

Tracked items (all created day -180):
  1. Levothyroxine 75mcg — once daily 06:30, empty stomach. metadata: {drug_name:"Levothyroxine", dosage:"75 mcg", form:"tablet", with_food:false, instructions:"30 min before breakfast"}
  2. Metformin 500mg — twice daily 09:00 and 21:00, with food
  3. Myo-Inositol 2g — once daily 09:00 (start_date = day -90, added later)
  4. Water target — 2500ml/day, every 120 min, 08:00–22:00
  5. Vitals tracking — no reminder; label for measurements only

Log entry generation (bulk of data — use batch SQLAlchemy inserts):
  Adherence per medication (weighted_action):
    Levothyroxine: 95% taken, 3% skipped, 2% missed. Skips weighted higher on weekends.
    Metformin 09:00: 88% taken, 8% skipped, 4% missed
    Metformin 21:00: 72% taken, 18% skipped, 10% missed  ← evening doses forgotten more
    Inositol: 85% taken, 10% skipped, 5% missed
  'Taken' occurred_at: fire_time + jitter(-15, +25) min
  'Skipped' occurred_at: fire_time + jitter(60, 180) min
  'Missed' = no log entry at all

Measurements:
  Weight: every 7 days. Start 78.4 kg, trend to 74.1 kg, ±0.4 jitter, occasional plateau.
  BP: every 14 days. Systolic 118–128, diastolic 78–84.
  Fasting glucose: 5 readings, 96–108 mg/dL.

Lab reports (4 reports):
  day -180: TSH 8.2 (HIGH), Free T4 0.7 (low-normal), Fasting glucose 102, HbA1c 5.7%, Total cholesterol 198, LDL 118, HDL 52, TG 142, Vit D 18 (LOW), B12 380
  day -120: TSH 4.1, Free T4 1.1, HbA1c 5.6%
  day -60:  TSH 3.2, Free T4 1.3, Fasting glucose 94, HbA1c 5.5%, Vit D 32 (normalized)
  day -10:  TSH 2.8, Free T4 1.4, HbA1c 5.4%, Lipid panel (Total 184, LDL 108, HDL 55)
  Story arc: thyroid treatment working, prediabetes prevented, Vit D corrected.

─────────────────────────────────────────────────────────

USER B — Rajesh, 58, male, HTN + Type 2 diabetes (240 days)

Profile: device_id='demo-seed-rajesh', name='Rajesh', age=58, gender='male'

Tracked items (all day -240):
  1. Amlodipine 5mg — once daily 08:00
  2. Telmisartan 40mg — once daily 08:00 (same slot as Amlodipine — must render both correctly)
  3. Metformin 1g — twice daily 08:00 and 20:00
  4. Atorvastatin 10mg — once daily 22:00
  5. Water target — 3000ml/day

Adherence:
  Amlodipine: 91%; Telmisartan: 88%
  Metformin 08:00: 84%; Metformin 20:00: 65%  ← evening dropoff
  Atorvastatin (22:00): 65%  ← late-night miss
  Stress event: day -120 to -113, all adherence drops to ~30%.
    This must produce a visible dip in 90-day and 180-day adherence charts.

Measurements:
  BP: daily 07:00, 240 readings. Baseline systolic 138–148 / diastolic 86–94.
      During stress week: spike to 158–168 / 96–104. Trend gradually back after.
  Weight: weekly, flat 84–86 kg ±0.6 jitter.
  Fasting glucose: every 30 days → 128 → 122 → 118 → 115 (slow improvement).

Lab reports (5 reports at day -240, -180, -120, -60, -15):
  Each includes: HbA1c, fasting glucose, full lipid panel, creatinine, eGFR, ALT, AST.
  HbA1c arc: 8.4 → 8.1 → 7.9 → 7.6 → 7.2
  LDL arc: 142 → 128 → 118 → 108 → 96 (statin working)
  eGFR: 78 → 76 → 75 → 73 → 72 (mild decline — flag as warning on latest)
  ALT day -60: 58 U/L (HIGH — incidental finding)

─────────────────────────────────────────────────────────

USER C — Anjali, 29, female, fitness-focused (21 days)

Profile: device_id='demo-seed-anjali', name='Anjali', age=29, gender='female'

Tracked items (day -21):
  1. Water target — 2500ml/day, every 90 min, 07:00–22:00
  2. Multivitamin — once daily 09:00 (start_date = day -10, partial period)
  3. Strength workout — Mon/Wed/Fri at 18:00

Adherence:
  Water: 5/7 days/week (realistic noisy)
  Multivitamin: 90% in 10 days of data
  Workout: 80%

Measurements: weight 3 entries → 58.2 → 58.4 → 58.1 (flat, low data)
Lab reports: 1 report day -5. Standard CBC + metabolic panel, all normal. No flags.

Point of Anjali: every dashboard must handle sparse data, partial periods, no chronic meds.
  30-day adherence uses 21 days as denominator.
  Lab trend view handles n=1 gracefully (single point, no line).

─────────────────────────────────────────────────────────

common.py helpers:

  IST = ZoneInfo("Asia/Kolkata")
  def days_ago(n): return datetime.now(IST) - timedelta(days=n)
  def jittered_time(base, lo, hi): return base + timedelta(minutes=random.randint(lo, hi))
  def weighted_action(weights: dict[str, float]) -> str | None:
    # weights = {'taken': 0.88, 'skipped': 0.08, 'missed': 0.04}
    # Returns action name or None for 'missed'

file_url: leave NULL on all demo lab reports. Add note="Demo data, no file attached".

Tests in tests/scripts/test_seed_demo.py:
  test_idempotent — run twice, assert identical row counts + content hash of key fields
  test_safety_production_guard — ENV=production, assert seed refuses with exit code 1
  test_safety_user_count_guard — pre-seed 60 non-demo users, assert seed refuses
  test_priya_adherence — Levothyroxine taken/(taken+skipped+expected) is in [0.93, 0.97]
  test_rajesh_stress_week_visible — day -120 to -113 adherence < 40% vs overall ~80%

On completion, print summary:
  Priya:   1 user, 4 tracked items, 5 reminders,  941 log entries, 26 measurements, 4 lab reports
  Rajesh:  1 user, 5 tracked items, 6 reminders, 1547 log entries, 264 measurements, 5 lab reports
  Anjali:  1 user, 3 tracked items, 4 reminders,  168 log entries, 3 measurements, 1 lab report

Anti-checklist:
  ❌ Don't use Faker for clinical values — use the hand-tuned numbers above
  ❌ Don't make adherence uniformly random — build in the Rajesh stress week and evening dropoff
  ❌ Don't generate placeholder PDFs — leave file_url NULL
  ❌ Don't seed log entries for future dates

Acceptance criteria:
  1. Completes in <10 seconds on t3.small
  2. Idempotent: two runs produce identical row counts and content hash
  3. ENV=production → refuses with exit code 1
  4. GET /upcoming?hours=18 as demo-seed-rajesh → all four 8am medications in correct order
  5. GET /measurements?type=bp_systolic as Rajesh → 240 readings with stress-week spike visible
  6. Priya Levothyroxine 30-day adherence in [0.93, 0.97]
```

---

## 7. Design reference — generate before P8

Before starting mobile work, generate a visual mockup of the Today screen so Prompt P9 has a design contract to match.

**Best tools (in preference order):**
1. **v0.dev** — best for high-fidelity mobile UI from text prompts
2. **Lovable.dev** or **bolt.new**
3. **Claude.ai** (fresh chat) — ask for HTML/Tailwind mobile mockup, screenshot it

After generating: save the screenshot to `~/Code/vital/design-refs/today-screen.png`. When running P9, attach this image and add the preface:
> Reference image attached. Where image and prompt disagree, the prompt's hex codes and structural rules win.

**Design prompt (paste into your tool of choice):**

```
Design a single mobile screen (390 × 844 px) for a premium health-tracking app called Vital. Aesthetic: editorial clinical — refined medical journal with earthy warmth. Like Monocle magazine layout discipline + NEJM restraint + Aesop palette + Apple Health data clarity.

═══ STRICT RULES — DO NOT VIOLATE ═══
- No purple-to-pink gradients, no multi-stop gradients
- No glassmorphism, no frosted blurs, no glow
- No neon, electric blue, cyan, fluorescent anything
- No emoji in UI
- No 3D/claymorphic icons — outline only, 1.5px stroke
- No pill-shaped buttons, no rounded blobs — radius 8–10px max
- No shadows except one barely-perceptible card shadow on Today cards
- Colour encodes meaning only, never decoration

═══ COLOUR SYSTEM ═══
Background:       #F7F4ED  (warm bone)
Card surface:     #FFFFFF with 1px border #E8E3D8
Primary text:     #1A1A1A
Secondary text:   #5C5C5C
Tertiary/labels:  #8C8C8C
Hairline borders: #E8E3D8
Subtle divider:   #F0EBE0

Category accents (muted, journal-quality):
  Medication:  #4A5D7E  (slate navy)
  Hydration:   #5B8A8F  (muted seafoam)
  Activity:    #8B5A3C  (warm clay)
  Nutrition:   #7A6F4D  (olive ochre)
  Vitals:      #6B4E71  (dusky plum)
  Custom:      #6B6F4D  (sage)

Status colours:
  Taken/on-target:  #3F6B4E  (muted forest)
  Pending/upcoming: #B07A1F  (warm amber — only for overdue items)
  Missed/overdue:   #B85C3C  (muted terracotta)

═══ TYPOGRAPHY ═══
Display/large numbers: Fraunces variable serif, semibold ~580, tight leading 1.1
Body/UI:               Geist Sans (400, 500, 600)
Timestamps/numbers:    Geist Mono (400, 500)
Section labels:        Geist Sans uppercase 11px letter-spacing 0.08em #8C8C8C

═══ SCREEN CONTENT (top to bottom) ═══

1. STATUS BAR — iOS, background #F7F4ED

2. HEADER (24px top, 20px horizontal)
   Left: "Good morning, Niranjan" Fraunces 28px #1A1A1A semibold, tight leading
         "Wednesday, 20 May" below in Geist Mono 13px #8C8C8C
   Right: Settings icon lucide outline 1.5px 22×22 #5C5C5C

3. SECTION LABEL "TODAY" — Geist Sans uppercase 11px #8C8C8C, 32px top margin

4. TIMELINE (5 items, 14px gap, 20px horizontal padding)
   Each item is a card: white, 1px border #E8E3D8, 8px radius, 14px/16px padding
   Left: 3px-wide vertical accent strip in category colour, clips to card left edge
   Layout row 1: title (Geist Sans 15px/500 #1A1A1A) + time right (Geist Mono 13px #5C5C5C)
   Layout row 2: subtitle (Geist Sans 13px #8C8C8C)
   Layout row 3 (pending only): action row — 36px tall, 8px gap
     [Taken] flex:2, #1A1A1A fill, #FFFFFF text, 8px radius
     [Clock icon] flex:1, hairline border, Snooze affordance
     [X icon]    flex:1, hairline border, Skip affordance
   
   The 5 items:
   08:00 — Pill icon #4A5D7E — Metformin 500mg / with breakfast
           STATE: taken → strip turns #3F6B4E, card bg #EAF0EC, action row removed, ✓ 8:02 AM
   09:30 — Droplet icon #5B8A8F — Hydration / 250 ml
           STATE: taken → same taken treatment
   12:00 — Utensils icon #7A6F4D — Lunch / Light meal
           STATE: pending (future) → full opacity, action row visible
   17:30 — Dumbbell icon #8B5A3C — Strength workout / 45 min · Gym
           STATE: pending (future)
   20:00 — Pill icon #4A5D7E — Metformin 500mg / with dinner
           STATE: pending (future)

5. SECTION LABEL "RECENT" (32px top, 16px bottom)

6. MEASUREMENT CARDS (horizontal scroll, 3 cards, 160×140px, 12px gap, 1px border #E8E3D8, 12px radius)
   Card 1 — WEIGHT: label uppercase #6B4E71, value "72.4" Fraunces 36px, "kg" Geist Sans 14px #8C8C8C, "▼ 0.8 kg" Geist Mono 12px #3F6B4E, sparkline 14-day #1A1A1A 1.5px
   Card 2 — BLOOD PRESSURE: "118/76" Fraunces 36px, "mmHg" beside, "WITHIN RANGE" pill background #F0EBE0 text #3F6B4E, dual sparkline
   Card 3 — HBA1C: "5.6" Fraunces 36px, "%" beside, "Last 4 months" Geist Mono 12px #8C8C8C, 6-point sparkline

7. SECTION LABEL "THIS WEEK" (32px top)

8. WEEKLY STATUS BLOCK — white card 1px border, 12px radius, 18px padding, 3 rows 12px gap
   Each row: 6×6 #3F6B4E dot + text with bolded key phrase
   "5 of 7 days on water goal." | "BP stable across 4 readings." | "No missed medications."

9. BOTTOM TAB BAR — 56px, 1px top border #E8E3D8, bone background
   Today (active: ink, 2px × 18px #4A5D7E bar left of icon), Library, Insights, Settings

═══ MOOD CHECK ═══
Should feel like a page from a well-designed health journal.
NOT a fitness app. NOT fintech. NOT monochrome graveyard.
Premium, calm, signal-rich. Trustworthy enough for a 50-year-old managing hypertension.
```

---

## 8. Mobile prompt queue

Run these in `vital-mobile/` after all backend prompts (P0–P7) are complete.

---

### P8 — Mobile repo scaffold + OpenAPI typegen + design system

```
Initialize a NEW git repository at the current directory (NOT inside kyros-backend). This is the Phase 1 Vital wellness app. Brand: Vital. Separate deploy lifecycle.

Start with:
  npx create-expo-app@latest . --template blank-typescript
  Then add expo-router.

Structure:
  app/
    _layout.tsx                  # root: ThemeProvider, QueryClientProvider, font loader
    (tabs)/
      _layout.tsx                # bottom tabs config
      index.tsx                  # Today
      library.tsx                # Library
      insights.tsx               # Insights
      settings.tsx               # Settings
    item/
      [id].tsx                   # tracked item detail
      new.tsx                    # category picker
      new/
        medication.tsx
        water.tsx
        workout.tsx
        meal.tsx
        custom.tsx
    lab/
      [id].tsx
      new.tsx
    measurement/
      new.tsx
      [type].tsx
    onboarding.tsx               # first-run onboarding + profile setup

  src/
    api/
      client.ts                  # fetch wrapper with X-Device-Id from expo-secure-store
      generated/
        schema.ts                # openapi-typescript output — COMMITTED to repo
      queries.ts                 # TanStack Query hooks using generated types
    theme/
      tokens.ts                  # exact colour/type/spacing/radii per section 5
      typography.ts              # text style presets
      ThemeProvider.tsx
    components/
      Screen.tsx
      Card.tsx
      Text.tsx
      Button.tsx
      ListItem.tsx
      Sparkline.tsx
      Input.tsx
      Select.tsx
      TimePicker.tsx
      DayOfWeekPicker.tsx
      StatusBadge.tsx
      EmptyState.tsx
      today/
        ReminderCard.tsx         # inline-action card (see P9 for full spec)
    notifications/               # placeholder for P12
      .gitkeep
    schedule/                    # placeholder for P11
      .gitkeep
    hooks/
    utils/

  scripts/
    sync-types.ts                # downloads openapi.json, runs openapi-typescript

  .env.example                   # EXPO_PUBLIC_API_URL, EXPO_PUBLIC_ENV
  app.json                       # name='Vital', slug, ios.bundleId, android.package
  package.json
  tsconfig.json                  # strict mode
  README.md
  .gitignore
  eas.json                       # EAS Build config placeholder

Dependencies (pnpm preferred):
  expo-router, expo-font, expo-secure-store, expo-image-picker, expo-document-picker,
  expo-notifications, expo-haptics, expo-linking, expo-web-browser
  @tanstack/react-query@5
  react-hook-form, @hookform/resolvers, zod
  react-native-gesture-handler  ← required for ReminderCard long-press
  date-fns, date-fns-tz
  victory-native, react-native-skia
  lucide-react-native, react-native-svg
  openapi-typescript, openapi-fetch (dev deps)
  @testing-library/react-native, jest-expo, @types/jest (dev)

OpenAPI typegen workflow:
  scripts/sync-types.ts:
    1. Fetch openapi.json from OPENAPI_URL env OR read ../kyros-backend/openapi.json
    2. Pipe through openapi-typescript → src/api/generated/schema.ts
    3. Add generated banner comment with timestamp
  package.json script: "sync:types": "tsx scripts/sync-types.ts"

API client (src/api/client.ts):
  - Stores device_id in expo-secure-store, generates uuid v4 on first run
  - Adds X-Device-Id header automatically
  - Type-safe via openapi-fetch (inferred from OpenAPI spec)
  - Handles 4xx (throw parsed error body), 5xx (generic message)
  - Supports multipart for lab-reports POST

Theme system (src/theme/tokens.ts):
  Export ALL tokens from section 5 of the build spec exactly as specified:
  colours (bone, paper, ink, slate, mist, hairline, divider, tealDeep, positive, warning,
           critical, missed, takenWash, snoozedWash, chartLine,
           categoryMedication, categoryHydration, categoryActivity, categoryNutrition,
           categoryVitals, categoryCustom)
  spacing (s4, s8, s12, s16, s24, s32, s48)
  radii (card: 8, button: 10, md: 8)
  typography presets (displayXL, displayL, displayM, h1, h2, body, bodySmall, caption, label, mono)

Font loading in app/_layout.tsx:
  useFonts from expo-font: Fraunces variable, Geist Sans (400/500/600), Geist Mono (400/500).
  Blank loading screen until fonts ready. 5s fallback to system fonts.

Component primitives (all use theme tokens — never inline hex):
  Screen: SafeAreaView, bone background, padding presets
  Card: paper surface, 1px hairline border, 8 radius. `elevated` prop adds subtle shadow.
  Text: variant prop (typography preset), color prop (token name)
  Button: variants 'primary'/'secondary'/'ghost', sizes sm/md/lg
  ListItem: left slot, title+subtitle, right slot, tappable
  Sparkline: SVG line, no axes, no fill, configurable stroke + width
  Input: bordered, focused=ink border, error=critical border
  Select: chevron + bottom sheet for options
  TimePicker: wraps @react-native-community/datetimepicker, outputs "HH:mm"
  DayOfWeekPicker: 7 toggleable pills, first letter of weekday in mono
  StatusBadge: small uppercase label, color by variant
  EmptyState: centred title + body + optional CTA, no illustration

Bottom tabs (app/(tabs)/_layout.tsx):
  4 tabs: Today (Home), Library (Layers), Insights (LineChart), Settings (Settings)
  1px hairline top border, bone background
  Active: ink. Inactive: mist. No badge bubbles.
  Active indicator: 2px × 18px vertical bar in categoryMedication (#4A5D7E) left of icon.

All 4 tab screens render EmptyState placeholders.

Tests: jest-expo configured. Smoke test per primitive: renders without crashing, snapshot.

After completion:
  - pnpm sync:types (with backend running)
  - pnpm ios or pnpm android
  - Screenshot empty Today screen showing Fraunces typography and tab bar
  - Verify src/api/generated/schema.ts generated correctly
```

---

### P9 — Today dashboard

```
Implement the Today screen at app/(tabs)/index.tsx.

This screen polls GET /v1/wellness/reminders/upcoming?hours=18 every 30 seconds (TanStack Query refetchInterval). Also refetchOnWindowFocus: true so coming back to the app refreshes immediately.

─────────────────────────────────────────────────────────
LAYOUT (top to bottom)
─────────────────────────────────────────────────────────

1. Header row
   - Greeting in Fraunces displayM — "Good morning, [name]" / "Good afternoon, [name]" / "Good evening, [name]"
     based on local time. [name] is fetched from GET /v1/users/me. If name is null, show "Good morning" without a name.
   - Date below in Geist Mono caption, slate ("Wednesday, 20 May")
   - Settings icon top-right (lucide Settings, slate)

2. TODAY section
   - Section label "TODAY" in caption, uppercase, letter-spaced, mist
   - Vertical timeline of upcoming reminders (18h window)
   - Each item renders as a ReminderCard component (see below)
   - 12px gap between cards, 20px horizontal padding

3. RECENT section
   - Section label "RECENT"
   - Up to 3 Sparkline cards, horizontally scrollable
   - Each card: type name uppercase, latest value Fraunces displayL with unit in body slate,
     14-day sparkline below, trend indicator (▲/▼/—) with delta vs 30-day average
   - Tap → /measurement/[type]

4. THIS WEEK section
   - Section label "THIS WEEK"
   - White card, hairline border, 18px padding
   - 2–3 plain text status lines computed locally from logs/measurements
   - e.g. "5 of 7 days on water goal.", "BP stable across 4 readings.", "No missed medications."
   - Each row: 6×6 token.positive dot + sentence with key phrase in medium weight

5. Empty states
   - No reminders → EmptyState "Nothing scheduled today", subtitle "Add from Library", ghost button "Open Library"
   - No measurements → suppress section
   - No weekly data → suppress section

Section spacing: 32px between sections.

─────────────────────────────────────────────────────────
ReminderCard component — src/components/today/ReminderCard.tsx
─────────────────────────────────────────────────────────

Build this as the TODAY screen's timeline item from the start — do NOT use a bottom sheet. The design is one-tap logging with an inline Undo affordance.

Props:
  reminderId: string
  trackedItemId: string
  category: 'medication'|'hydration'|'activity'|'nutrition'|'vitals'|'custom'
  title: string         // e.g. "Atorvastatin"
  subtitle: string      // e.g. "10 mg · 1 tablet"
  fireAt: string        // ISO datetime
  state: 'pending'|'taken'|'skipped'|'snoozed'
  actionAt?: string     // ISO datetime, present when state !== 'pending'
  snoozeUntil?: string  // ISO datetime, present when state === 'snoozed'
  isOverdue: boolean    // fireAt < now && state === 'pending'

Card visual (all states):
  White background (tokens.paper), 0.5px border tokens.hairline, radius tokens.radius.md (8px)
  3px-wide vertical accent strip on left edge — category colour in pending; tokens.positive in taken; tokens.mist in skipped; tokens.warning in snoozed.
  overflow: hidden (strip bleeds into card left edge, no gap)
  Inner padding: 12px vertical, 14px horizontal

PENDING state:
  Row 1: title (Geist Sans 15px/500, ink) + time right (Geist Mono 13px, slate if on-time, warning if overdue)
  Row 2: subtitle (Geist Sans 13px, slate), 4px below title
  Row 3: action row, 10px below subtitle, 36px tall, 8px gap between buttons:
    [Taken]  flex:2, background tokens.ink, text tokens.paper, 13px/500, radius 8px — tap → 'taken' mutation
    [Clock]  flex:1, hairline border, lucide Clock icon 16px stroke 1.5 tokens.ink — tap → snooze 15min; long-press 500ms → inline duration picker (15min/30min/1hr, NOT a bottom sheet)
    [X]      flex:1, hairline border, lucide X icon — tap → 'skipped' mutation
    accessibilityLabel: "Snooze 15 minutes" and "Skip" respectively

TAKEN state (card transforms in-place without layout shift):
  - Card background → tokens.takenWash (#EAF0EC, ~6% saturation — do NOT brighten)
  - Left strip → tokens.positive
  - Time right → lucide Check 13px tokens.positive + action time in Geist Mono 13px tokens.positive ("✓ 8:02 AM")
  - Subtitle row: append " · Taken · Undo" where Undo is tappable underlined text
  - Action row: removed. Card shrinks vertically by ~46px.

SKIPPED state:
  - Card bg unchanged (white)
  - Left strip → tokens.mist
  - Title: textDecorationLine 'line-through', color tokens.slate
  - Time right → "Skipped" Geist Sans 13px tokens.mist
  - Card opacity 0.65 (recedes visually)
  - Subtitle row: append " · Undo"
  - Action row: removed

SNOOZED state:
  - Card bg → tokens.snoozedWash (#FBF3E3, ~6% saturation — do NOT brighten)
  - Left strip → tokens.warning
  - Time right → "Back at HH:MM" Geist Mono 13px tokens.warning (snoozeUntil formatted in user locale)
  - Subtitle row: append " · Undo"
  - Action row: removed

Undo affordance (critical — do NOT skip):
  - Local state: undoExpiresAt: number | null
  - On mutation success: undoExpiresAt = Date.now() + 8000, setTimeout to clear
  - Undo text visible ONLY while undoExpiresAt > Date.now()
  - Undo tap: calls useUndoLogEntry mutation → immediate cache invalidation → card returns to pending
  - Never a modal, toast, or sheet — inline only

Snooze long-press:
  - Long-press 500ms on Clock button opens small inline popover ABOVE the button (not a sheet)
  - Three options: "15 minutes" / "30 minutes" / "1 hour"
  - Tap selects → mutation with snoozeMinutes → popover dismisses
  - Tap outside → dismiss without action
  - Use react-native-gesture-handler LongPressGestureHandler

Mutations — create these hooks:
  src/hooks/useLogReminder.ts:
    TanStack Query mutation: { reminderId, fireAt, action, snoozeMinutes? }
    Optimistic update: immediately update /reminders/upcoming cache
    On error: rollback cache, show non-blocking inline error (not a toast library)
    On success: invalidate /reminders/upcoming AFTER 8-second Undo window closes (not immediately)
    Backend calls: POST /v1/wellness/logs

  src/hooks/useUndoLogEntry.ts:
    Soft-deletes most recent log for (reminderId, fireAt)
    Backend call: DELETE /v1/wellness/logs/{id}
    On success: invalidate /reminders/upcoming immediately

Animation (minimal — do not add more):
  - Height change when action row removes: LayoutAnimation.configureNext(easeInEaseOut, 200ms)
  - Background colour fade: Animated.timing on opacity, 180ms
  - Nothing else

Accessibility:
  - accessibilityRole="button" on each action
  - Card accessibilityLabel: "${title}, ${state === 'pending' ? 'due at' : 'logged at'} ${formattedTime}"
  - After action: AccessibilityInfo.announceForAccessibility("${title} marked as ${action}")

Haptics:
  Taken → Haptics.notificationAsync(NotificationFeedbackType.Success)
  Skip/Snooze → Haptics.selectionAsync()
  That is the ONLY haptic.

NOT in this component:
  ❌ No bottom sheets for actions
  ❌ No global state library (TanStack Query cache is source of truth)
  ❌ No streaks, badges, points, confetti, gamification
  ❌ No "Mark all taken" bulk action
  ❌ No additional animations beyond the two listed
  ❌ Do not skip the Undo affordance

Tests in src/components/today/__tests__/ReminderCard.test.tsx:
  - Renders all four states (snapshot per state)
  - Tapping Taken fires mutation with action:'taken'
  - Tapping Skip fires mutation with action:'skipped'
  - Short-press Snooze fires mutation with action:'snoozed', snoozeMinutes:15
  - Long-press Snooze opens picker; selecting "1 hour" fires snoozeMinutes:60
  - Undo visible 8s after action, then disappears
  - Tapping Undo within window fires delete mutation
  - Overdue pending shows time in tokens.warning

Acceptance criteria for this prompt:
  1. From seeded demo data (Priya, Levothyroxine pending 6:30 AM), tap "Taken" → entry logged, card transforms, Undo shows for 8s. One tap, no layout shift.
  2. Tap Undo within 8s → card returns to pending, log entry deleted (verify via GET /v1/wellness/logs).
  3. Long-press Snooze → inline picker; any option fires mutation correctly.
  4. On 320px wide screen, all action buttons remain tappable (≥44px touch target).
  5. Window-focus refetch works: background the app and return → Today refreshes.

After completion: seed backend via `poetry run python -m scripts.seed_demo`, attach the design-refs/today-screen.png image, then run the app and compare the Today screen against the reference image.
```

---

### P10 — Library + tracked item CRUD UI

```
Implement the Library tab and tracked-item create/edit flows.

Library screen (app/(tabs)/library.tsx):
  Header: "Library" in Fraunces displayM, plus icon top-right → /item/new
  Filter chips row: All, Medication, Water, Meals, Workout, Vitals, Custom
    ink active, slate inactive, hairline borders, no fills
  Sectioned list grouped by category:
    Section header: label caption uppercase mist
    Each row: ListItem with category icon, name + subtitle (e.g. "Metformin 500mg · 2x daily"), mist chevron
    Tap → /item/[id]
  "Lab reports" section below tracked items: list cards with date, lab name, flagged count. Tap → /lab/[id].
  Empty state: "No tracked items yet", "Add medications, water goals, workouts and more.", primary button "Add your first item"

Category picker (app/item/new.tsx):
  Vertical list of 6 large cards, one per category, with icon + name + one-line description.
  Tap → /item/new/[category]

Per-category create forms:

  Medication form:
    drug_name (text, required)
    dosage (text, "500 mg", required)
    form (segmented: tablet/capsule/syrup/injection/other)
    times_per_day (stepper 1–6)
    specific_times[] (TimePicker per dose, defaults spread across waking hours)
    days_of_week (DayOfWeekPicker, default all)
    with_food (toggle)
    start_date (date picker, default today)
    end_date (optional, "Ongoing" toggle)
    instructions (multiline, optional)

  Water form:
    daily_target_ml (default 2500)
    reminder_interval_minutes (default 120)
    active_window start/end (TimePicker, 08:00–22:00)

  Workout form:
    workout_type (text)
    duration_minutes (number)
    days_of_week (DayOfWeekPicker)
    time_of_day (TimePicker)
    location (text, optional)

  Meal form:
    meal_name (text, e.g. "Breakfast")
    time (TimePicker)
    days_of_week (DayOfWeekPicker)
    notes (multiline, optional)

  Custom form: title, message, full ScheduleBuilder (see P11)

On save: POST /tracked-items then POST /tracked-items/:id/reminders (schedule JSON built from form). Navigate back to Library.

Tracked item detail (app/item/[id].tsx):
  Header: item name displayM, category badge
  "Reminders" section: list with schedule summary in plain English ("Daily at 8:00 AM and 8:00 PM")
  "Recent activity": last 10 log entries (time + action)
  "Adherence (last 30 days)": taken/(taken+skipped+expected fires) percentage
  Buttons: Edit (prefilled form), Pause/Resume (toggle status), Discontinue (soft delete + confirm)

Forms: react-hook-form + Zod resolvers.

After completion: create one item of each category through UI, verify they appear in Library and on Today.
```

---

### P11 — Reminder builder + schedule UI primitives

```
Build the reusable ScheduleBuilder used by the Custom form (and internally by other category forms).

Components in src/components/schedule/:

  ScheduleBuilder.tsx — top-level, value/onChange for schedule JSON.
    Segmented control: "At specific times" / "Every few hours"
    Renders RecurringBuilder or IntervalBuilder.
    Defaults timezone to device timezone.
    Validates via scheduleSchema.parse() on blur.
    Shows inline error text (tokens.critical) under field if invalid.
    Emits schedule JSON that round-trips through scheduleSchema.parse() without loss.

  RecurringBuilder.tsx — times[] with add/remove rows (TimePicker per row); DayOfWeekPicker; optional date range with "Ongoing" toggle.

  IntervalBuilder.tsx — interval_minutes input ("Every 1h", "Every 2h" labels), active_window start/end TimePickers, DayOfWeekPicker.

Integrate ScheduleBuilder into Custom form. Other category forms construct the schedule JSON internally — users don't see the full builder for medication/water/workout/meal.

Tests in src/components/schedule/__tests__/:
  - Recurring "8am and 8pm every day" output matches expected JSON
  - Interval "every 2h, 8–22, weekdays" output matches expected JSON
  - End time before start time shows inline error

After completion: create a Custom item with schedule "every 90 min, 09:00–18:00, weekdays". GET /upcoming?hours=48 and verify correct expansion.
```

---

### P12 — Local notification engine

```
Wire up local notifications using expo-notifications.

Files:
  src/notifications/permissions.ts  — requestPermissions(), returns granted/denied
  src/notifications/scheduler.ts    — sync(): fetch /reminders/upcoming?hours=72, diff against scheduled local notifications, cancel obsolete, schedule new. Each notification identifier = fire_key.
  src/notifications/handlers.ts     — notification action handler: tap 'Taken'/'Skipped'/'Snooze 15m' → POST /logs with fire_key. Snooze: schedule one-off local notification now+15min.
  src/notifications/categories.ts   — register categories "MEDICATION" (Taken/Skipped/Snooze), "WATER", "WORKOUT", "MEAL" with appropriate actions.

Behaviour:
  - On app foreground: scheduler.sync() runs once
  - On any tracked_item or reminder mutation: invalidate + refetch + reschedule
  - On permission denied: non-blocking banner on Today linking to Settings → Notifications
  - Snooze 15m: local notif now+15min, no API call (log goes through when user taps Taken)

Edge cases:
  - App killed: local notifications still fire (the point of local, not push)
  - Timezone change: scheduler.sync() detects and re-syncs
  - DST: handled by expand_schedule (already tested in P2)
  - Permission revoked between sessions: detected on foreground, banner shown

Settings tab additions:
  - Toggle: Notification permissions (deep link to OS settings if denied)
  - Toggle: Notification sound on/off
  - Timezone display (read-only, from device)

After completion: create medication with reminder 2 minutes out, lock device, wait for notification, tap "Taken" from lock screen, verify log entry appears on Today.
```

---

### P13 — Measurements + charts

```
Implement measurements feature.

Screens:

  app/measurement/new.tsx:
    Type select: weight/BP systolic+diastolic/heart rate/fasting glucose/HbA1c/body temp/steps
    For BP: systolic + diastolic as single form → two measurement rows with same measured_at
    Value (numeric keypad), unit (auto-set per type, editable), measured_at (default now), note (optional)
    Submit → POST /measurements

  app/measurement/[type].tsx:
    Header: type name displayM, latest value displayXL Fraunces with unit body slate, trend indicator vs 30d avg
    Time range chips: 7d / 30d / 90d / 1y / All (ink active)
    Chart: Victory Native XL line chart, chartLine stroke 1.5px, no fill, hairline x-axis only, y-axis labels Geist Mono slate
    Reference range band: translucent hairline horizontal stripe if reference_range present
    Below chart: individual measurements with edit/delete swipe actions
    BP: two lines (systolic ink, diastolic slate)

Wire Today RECENT sparklines to deep-link into /measurement/[type].

Chart utilities in src/charts/:
  formatValue(type, value) → formatted string with unit
  trendDirection(values) → 'up'|'down'|'flat' + delta percentage
  mergeBPRows(measurements) → pairs systolic + diastolic by measured_at

After completion: 30 days of weight, verify 30d chart + trend indicator. 10 BP readings, verify dual-line chart.
```

---

### P14 — Lab reports

```
Implement lab report capture and viewing.

Screens:

  app/lab/new.tsx:
    Camera/Gallery/PDF picker (expo-image-picker + expo-document-picker). Preview thumbnail.
    report_date (default today), lab_name (optional)
    Tests array (manually entered): name, value (string — "Negative" works), unit, ref_low?, ref_high?, flag (normal/low/high/critical)
    "Add another test" button
    Note (multiline, optional)
    Upload progress bar during multipart submit. Retry on network failure.
    Validation: at least one test row required.
    Submit → multipart POST /lab-reports

  app/(tabs)/library.tsx — lab reports section already added in P10

  app/lab/[id].tsx:
    Header: lab_name + report_date displayM
    "View original" button (expo-web-browser or in-app PDF viewer)
    Tests table: Geist Mono for values/ranges, flag badge (positive/warning/critical)
    Long-press a test row → "Convert to tracked measurement" (creates measurements row)
    Edit / Delete buttons in header

After completion: upload sample PDF with 6 tests (2 flagged), convert HbA1c to measurement, verify in /measurement/hba1c.
```

---

### P15 — Onboarding + insights + history + settings + polish

```
Final Phase 1 prompt. Ship remaining surfaces and polish.

─── Onboarding (app/onboarding.tsx — first-run, gated by AsyncStorage flag) ───

Four screens, swipeable:

  Screen 1: "Your wellness, in one place." + subtitle. Continue.

  Screen 2: "Reminders that respect your day." Body: manual, private, no account required. Continue.

  Screen 3: "Add what matters first." Continue.

  Screen 4 — Profile setup (new):
    Title: "A bit about you" in Fraunces displayM
    Subtitle: "Helps personalise your experience. You can skip and update later."
    Fields:
      Name (text input, placeholder "Your name", optional — but encouraged)
      Age (numeric input, optional)
      Gender (segmented/select: Male / Female / Other / Prefer not to say, optional)
    Buttons: [Save & continue] [Skip for now]
    On save: PATCH /v1/users/me with {name, age, gender} then route to Library/new
    On skip: route to Library/new (name/age/gender stay null)

  Note: The Today greeting "Good morning, [name]" fetches name from GET /me. If null, shows "Good morning" without a name.

─── Insights tab (app/(tabs)/insights.tsx) ───

Header "Insights" in displayM.
Three section cards:
  1. Adherence — last 30 days. Bar per category: % medications taken, % water goal days hit, % workouts completed. Ink and hairline bars only, no colour beyond ink.
  2. Trends — list of measurement types with 30-day direction (▲ ▼ —) and current value. Tap → /measurement/[type].
  3. Lab summary — count of reports, count of flagged tests in last 90 days.
Empty state until ≥7 days of data.

─── History (/history, accessible from Settings or Insights) ───

Filter chips: All / Medications / Water / Workouts / Meals / Custom
Date range picker
Vertical list of log_entries, newest first, infinite scroll
Each row: time (Geist Mono slate), item name, action badge ("Taken" positive, "Skipped" warning, etc.)

─── Settings tab (app/(tabs)/settings.tsx) ───

Account:
  - Shows name (editable inline or via a dedicated screen) — tap opens Profile edit screen
  - Shows "Guest mode" explanation, "Sign in to back up" stub
Notifications: toggle, deep link to OS settings
Timezone: read-only display from device
Data: Export all data (JSON), Delete all data (with confirm)
About: version, build, privacy policy (placeholder URL)

Profile edit screen (accessible from Settings):
  Same fields as onboarding screen 4: name, age, gender
  Submit → PATCH /v1/users/me
  Back button without save → discard changes

─── Edge case polish ───

Network error: slate banner top of screen, retry button, never blocks UI
Loading skeletons for all list screens (hairline placeholder bars, not spinners)
Pull-to-refresh on Today, Library, Insights
Accessibility: every Pressable has accessibilityLabel, semantic icons have accessibilityRole, font scales up to 1.3x without broken layouts
Haptics: already in P9 for reminder actions. No new haptics unless explicitly needed.

─── End-to-end acceptance run ───

1. Fresh install → onboarding → enter name="Niranjan", age=30, gender="Male" → Library
2. Create a medication
3. Receive a notification → tap Taken
4. Today screen shows greeting "Good morning, Niranjan"
5. View log in History
6. View adherence in Insights
7. Export data → JSON contains name, age, gender in user object
8. Verify Settings shows name, edit it → Today greeting updates
```

---

## 9. Order of execution

Run sequentially — each prompt depends on the previous. Do not parallelize.

| # | Prompt | Repo | Estimated Claude Code time |
|---|---|---|---|
| P0 | Backend repo scaffold | kyros-backend | 20–30 min |
| P1 | SQLAlchemy models + Alembic migrations | kyros-backend | 45–60 min |
| P2 | Pydantic schemas + core utilities | kyros-backend | 60–90 min |
| P3 | API foundations + users endpoint + OpenAPI export | kyros-backend | 45–60 min |
| P4 | Tracked items + reminders + upcoming fires | kyros-backend | 90–120 min |
| P5 | Logs + measurements + lab reports | kyros-backend | 90–120 min |
| P6 | Admin panel | kyros-backend | 90–120 min |
| P7 | Demo data seeding script | kyros-backend | 60–90 min |
| — | Generate design reference (section 7) | — | 30 min manual |
| P8 | Mobile scaffold + typegen + design system | vital-mobile | 90–120 min |
| P9 | Today dashboard + ReminderCard | vital-mobile | 90–120 min |
| P10 | Library + tracked item CRUD UI | vital-mobile | 120–180 min |
| P11 | Reminder builder + schedule UI | vital-mobile | 60–90 min |
| P12 | Local notification engine | vital-mobile | 90–120 min |
| P13 | Measurements + charts | vital-mobile | 90–120 min |
| P14 | Lab reports | vital-mobile | 90–120 min |
| P15 | Onboarding + insights + history + settings + polish | vital-mobile | 120–180 min |

**Total Claude Code time: ~20–28 hours of focused execution.**
Realistic calendar to first beta user: **4–6 weeks** including review time, EC2 deployment, App Store / Play Store submission, and testing group.

---

## 10. Lead-time items to start this week

These are the longest poles and don't depend on code:

1. **Domain registration + SSL** — lock the brand name and domain today.
2. **EC2 instance + S3 backup bucket** — provision t3.small in ap-south-1 now. Costs ~₹50/week idle.
3. **Apple Developer account (₹8,500/year)** — enrolment takes 2–7 days.
4. **Google Play Console account (one-time ₹2,000)** — enrolment takes 1–2 days.
5. **AiSensy WABA approval** — WhatsApp is Phase 2 but WABA approval takes 2–4 weeks. Apply now.
6. **Razorpay KYC** — Phase 2 dependency but KYC takes 3–4 weeks. Start month 3 of the build.

---

## 11. What Phase 2 adds (no Phase 1 rewrites)

1. `app/clinic/` populated: consultation, prescription, lab_order routes reading/writing the same DB.
2. `app/integrations/kyros_intake.py` — on first login, link `users.kyros_patient_id`.
3. `app/wellness/services/clinical_sync.py` — doctor prescription → `wn_tracked_item` with `source='kyros'`.
4. Mobile UI: "From your Kyros chart" badge on Kyros-sourced rows, lock direct edits.
5. Subscription gating: free / plus / kyros tier paywall logic.
6. WhatsApp channel in `reminders.channels`: Celery task dispatches via AiSensy.
7. OTP login with "Back up your data" upgrade prompt.

No schema migrations. No reminder engine rewrite. No dashboard redesign.

---

## 12. What Phase 3 adds (no Phase 1 rewrites)

1. **`POST /v1/wellness/capture`** — accepts image/audio/text. Routes to Gemini 2.5 Pro for lab OCR / prescription extraction, Claude Sonnet for medication-interaction summaries, Gemini Audio / Whisper for voice commands. Returns a draft the user confirms; confirmed records get `source='ai_extracted'`.
2. **Voice command interface** — push-to-talk button in the app.
3. **Per-channel dispatcher upgrades** — voice via Exotel TTS + outbound call API.

Data model already ready. Reminder schema already ready. Dashboard already reads from the same tables.




Updation of the app is a 3-step process:
# Build: Vital — Today screen (editorial-clinical health app)

Reference screenshots are attached. Where the screenshots and this prompt
disagree, this prompt's hex codes and structural rules win.

Target: a single mobile screen, **390 × 844 px** (iPhone 14). Production
React Native / Expo (or React + CSS, depending on the stack already in
your repo). Use the existing tokens file if one exists; otherwise create
`src/theme/tokens.ts` with the values below.

═══════════════════════════════════════════════
AESTHETIC
═══════════════════════════════════════════════
Editorial clinical. References: Monocle's category-tinted layouts,
the New England Journal of Medicine's restraint, Aesop's earthy
palette, Apple Health's data clarity, Things 3's typographic
confidence. Premium, calm, signal-rich. Never decorative.

═══════════════════════════════════════════════
STRICT RULES — DO NOT VIOLATE
═══════════════════════════════════════════════
- No purple-pink gradients. No multi-stop gradients of any kind.
- No glassmorphism, frosted blurs, glow.
- No neon, electric blue, cyan, fluorescent anything.
- No emoji anywhere in the UI.
- No 3D / claymorphic icons. Outline only, **1.5px stroke**.
- No pill-shaped buttons or rounded blobs. Radius **8–10px max**.
- No shadows except a barely-perceptible card shadow if needed.
- Colour must encode meaning. No decorative colour.

═══════════════════════════════════════════════
TOKENS
═══════════════════════════════════════════════
Surfaces & text
- bg:        #F7F4ED   (warm bone)
- card:      #FFFFFF
- hairline:  #E8E3D8   (1px borders, no shadows)
- divider:   #F0EBE0   (subtler internal divider)
- text:      #1A1A1A
- secondary: #5C5C5C
- tertiary:  #8C8C8C

Category accents (muted, journal-quality)
- medication: #4A5D7E   (slate navy)
- hydration:  #5B8A8F   (seafoam teal)
- activity:   #8B5A3C   (warm clay)
- nutrition:  #7A6F4D   (olive ochre)
- vitals:     #6B4E71   (dusky plum)
- custom:     #6B6F4D   (sage)

Status
- taken:    #3F6B4E
- pending:  #B07A1F
- missed:   #B85C3C
- critical: #8B2C1F

═══════════════════════════════════════════════
TYPOGRAPHY
═══════════════════════════════════════════════
- Display & large numbers:        Fraunces (variable serif, 600,
  tight leading 1.1, optical-size aware)
- Body & UI:                      Geist Sans (400, 500, 600)
- Numbers, times, sparklines:     Geist Mono (400, 500), tabular-nums
- Section labels:                 Geist Sans, uppercase, 10–11px,
  letter-spacing 0.08–0.12em, tertiary
- Body copy:                      14–15px, line-height 1.4

═══════════════════════════════════════════════
LAYOUT — TWO-ZONE TODAY SCREEN
═══════════════════════════════════════════════
The screen is split into two zones below a compact header. The user
scrolls each zone independently. The top zone is the reminder
timeline. The bottom zone is reports.

1. STATUS BAR
   Standard iOS 50px area, glyphs in primary text colour.

2. HEADER (padding 14px 20px 12px)
    - "Good morning, {Name}" — Fraunces 20px / 600, tight leading.
    - Below: "Wed, 20 May · HH:MM" in Geist Mono 11px, tertiary.
    - Top-right: outline Settings icon, 20px, secondary colour.
    - Below that: an "ADHERENCE" mini-strip:
        * Label uppercase 10px tertiary, "ADHERENCE"
        * Right: "n/total · pct%" in Geist Mono 11px (n bold)
        * 3px progress bar on divider colour, fill = taken green

3. TOP ZONE (fixed height 360px, border-bottom hairline)
   This zone has two stacked parts.

   3a. FOCUS CARD (the currently selected item)
   - White card, 1px hairline border, 10px radius, 4px thick
   left tint bar in the category accent.
   - Top row: small uppercase label ("UP NEXT" / "DUE NOW" /
   "COMPLETED" / "SKIPPED" / "MISSED") in the state's colour,
   a 3px dot, then a mono relative-time string
   ("In 4 h 45 min", "Overdue 15 min", etc.).
   Right of the row: a small Expand glyph button.
   - Title block:
   * 36px square category icon swatch on accent @ 8% alpha,
   radius 8, icon in category accent.
   * To its right: mono 12px time, then Fraunces 19px / 600
   title (strikethrough if taken), then sans 12px
   secondary subtitle.
   - Action row, 6px gap:
   * If pending (future):
   [Mark taken — green primary] [Snooze 10m — ghost]
   [Skip — ghost narrow]
   * If taken:
   [Undo — ghost] [Mark skipped — ghost]
   * If skipped or missed:
   [Mark taken (late) — green primary] [Undo — ghost]
   - The primary button is solid #3F6B4E, white text, 8px radius,
   9px vertical padding, sans 12px / 500.
   - Tapping the icon swatch, title, or expand glyph opens the
   full-screen detail overlay.

   3b. COMPACT TIMELINE LIST (scrollable, fills the rest of the zone)
   Chronological top→bottom. Single line per item:
   [40px time mono] [2px category tint bar 14px tall]
   [13px outline category icon in accent]
   [title sans 13px / 500] [subtitle 11px tertiary, ellipsis]
   [state glyph on the right, 12px]
   Selected row: 2px left border in primary text, soft divider
   background fill, time bold.
   Past non-taken rows: title secondary, time tertiary, faded
   category bar (opacity 0.5), faded icon (opacity 0.55).
   Past taken rows: title tertiary + strikethrough.

       State glyphs (right side, 12–14px):
         - taken:   filled-check green
         - skipped: circle with slash, missed-red
         - missed:  em-dash, missed-red
         - pending: outline circle, tertiary

       **NOW divider** is injected into the list at the right index
       (between the last past item and the first future item):
         [40px "NOW" sans 10px / 700]
         [mono current time]
         [thin 1px line, primary text, 65% opacity]

       On selection, the list auto-scrolls so the selected row is
       roughly vertically centred in the scroll viewport.

4. BOTTOM ZONE (flex 1, independent scroll)

   4a. RECENT VITALS — horizontal scroll, hide scrollbar
   Section header: "RECENT VITALS" label · hairline rule · "3 readings"
   Tiles, each 144×116, 12px padding, 10px radius, 1px hairline:
   * Tile label uppercase 10px in vitals accent (#6B4E71)
   * Value Fraunces 24px / 600 with tiny sans unit beside it
   * Delta line in Geist Mono 11px, colour = taken green for
   good direction, tertiary for neutral
   * BP tile replaces delta with a "WITHIN RANGE" pill —
   sans 9px / 500 / uppercase, taken-green text, divider bg,
   4px radius, 2px×5px padding
   * 120×20 sparkline at the bottom (mono primary line, no fill,
   1.5px stroke; BP gets dual line — diastolic in tertiary)

   4b. THIS WEEK — single white card, hairline, 10px radius
   Four lines, 9px gap:
   · status dot (5px circle) · sans 13px line.
   "5 of 7 days on water goal." — bold first chunk
   "BP stable across 4 readings." — "stable" bold
   "No missed medications." — "No missed" bold
   "Sleep below 7 h on 3 nights." — "Sleep" bold, pending-amber dot

5. TAB BAR (56px, hairline top border)
   4 tabs: Today / Library / Insights / Settings.
   Outline lucide-style icons, 22px, 1.5px stroke.
   Active tab: icon + label in primary text. A 2px × 18px slate-navy
   vertical bar sits 10px to the left of the active icon (NOT a pill).
   Labels sans 10px / 500.

6. HOME INDICATOR
   Standard 134×5 capsule, 28% black, centred 8px from bottom.

═══════════════════════════════════════════════
FULL-SCREEN DETAIL OVERLAY
═══════════════════════════════════════════════
Triggered by tapping the focus card's body, icon, or expand glyph.
Slides up 20px over 220ms with opacity 0→1.

Header (52px top padding, hairline bottom):
- Left: "REMINDER DETAIL" tertiary label.
- Right: close (✕) icon button, 20px primary text.

Body:
- Category strip: 6px dot in accent + uppercase 11px category label.
- Hero row: 52×52 icon swatch (accent @ 8% alpha) + title block:
    * mono time, "due now" / "in {dur}" suffix in tertiary
    * Fraunces 26px / 600 title, letter-spacing -0.5
    * sans 14px secondary subtitle
- State ribbon (only if past): coloured pill with glyph + label.
- "SCHEDULE" section: short sentence describing the rule.
- Hairline divider.
- "ADHERENCE — LAST 7 DAYS":
    * Fraunces 30px percent + mono 12px "n of 7 taken"
    * 7-segment bar strip (each segment flex 1, 28px tall):
      taken = green, skipped = divider colour, missed = missed-red
      @ 40% alpha
    * Mono 10px tertiary endpoints "13 May" / "Today"
- Hairline divider.
- "LOG": 7 rows of {date | time | UPPERCASE STATE}
  state colour = taken-green or missed-red.

Sticky footer (12px padding, hairline top):
- Same action row logic as the focus card, but at 12px padding,
  13px font, full-width primary button.

═══════════════════════════════════════════════
INTERACTION MODEL
═══════════════════════════════════════════════
- Default selected item = first pending/missed item at or after NOW.
- Tap any row in the timeline → it becomes the focus card; list
  auto-scrolls so it's centred.
- Tap any action on the focus card → state updates; selection moves
  back to the new "Up Next" automatically (except for Undo, which
  keeps selection).
- "Snooze 10m" pushes that item's time forward by 10 minutes; the
  list re-sorts.
- Tap focus card body, icon, or expand glyph → detail overlay.
- Time should be derived from the device clock; for development,
  expose a `nowMin` override (minutes since midnight) so layouts
  can be inspected at any hour.

═══════════════════════════════════════════════
SAMPLE DATA
═══════════════════════════════════════════════
Generate ~34 items spread across one day from 06:00 to 22:30
with categories medication / hydration / activity / nutrition,
representing a user who tracks:
- 10 medication doses
- 10 hydration cues (250 ml each)
- 1 strength workout, 8 walk-around micro-breaks
- 1 lunch, 1 stretch session
  States for past items: mostly taken, a couple skipped, none missed
  unless the past pending → missed rule kicks in.

═══════════════════════════════════════════════
ACCESSIBILITY
═══════════════════════════════════════════════
- All tap targets ≥ 44px high. Compact list rows currently render
  at 36px — make the *touch zone* extend to 44px even if the visual
  row is shorter.
- All buttons have accessibility labels.
- Colour is never the only signifier — every state has a glyph too.
- Text never smaller than 10px; only labels use 10–11px.

═══════════════════════════════════════════════
DELIVERABLES
═══════════════════════════════════════════════
1. `src/theme/tokens.ts` — every value above.
2. `src/screens/Today.tsx` — the screen.
3. `src/components/today/`:
   FocusCard, ListRow, NowMark, VitalTile, WeeklyStatus,
   DetailOverlay, TabBar, Header.
4. `src/data/sampleReminders.ts` — the seed list above.
5. No external icon packs; inline SVG (or react-native-svg) for the
   handful of icons used: Pill, Droplet, Utensils, Dumbbell, Heart,
   Home, Layers, Activity, Settings, Check, Slash, Circle,
   Chevron, Close, Expand.

Match the attached screenshots' proportions, spacing, and visual
weight. When in doubt, choose restraint.