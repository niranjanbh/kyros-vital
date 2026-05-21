# Wellness App — Phase 1 Build Spec & Claude Code Prompt Queue (v2: FastAPI stack)

Updated to match the Kyros backend stack — **one Python codebase serves both wellness (Phase 1) and clinic (Phase 2)**. The schema, mobile, and design system from v1 are unchanged. Backend prompts are rewritten for FastAPI + SQLAlchemy + Pydantic. Phase 1 infra path is now optimized for ~₹5K/month, not ₹1L.

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

9. **Guest mode in Phase 1.** No OTP, no login. `X-Device-Id` header identifies the user; the API finds-or-creates a `users` row on first hit. Saves MSG91 spend, removes the biggest onboarding drop-off. OTP arrives in Phase 1.5 with the "back up your data" upgrade prompt.

10. **Online-first, not offline-first.** App talks to the backend on every action. Offline sync is Phase 1.5 — a real 2-week project on its own, not needed to validate the product.

11. **Single EC2 box in Phase 1.** docker-compose with FastAPI + Postgres 16 + Redis on one t3.small in ap-south-1. Migrate to managed services (RDS, ElastiCache, ECS Fargate) only when MRR justifies it.

12. **The mobile app is its own repo.** `vital-mobile` (Expo) is a separate git repo from `kyros-backend`. They share types via committed `openapi.json` consumed by `openapi-typescript`. Independent deploy cycles.

---

## 2. Tech stack (locked, matching Kyros)

### Backend — `kyros-backend` repo

| Layer | Choice | Notes |
|---|---|---|
| Language | **Python 3.12** | Matches Kyros, your strength |
| Framework | **FastAPI 0.115+** | Async, auto OpenAPI for mobile typegen |
| ORM | **SQLAlchemy 2.0 async** | Typed Mapped[] style |
| Validation | **Pydantic v2** | Discriminated unions for schedules |
| Migrations | **Alembic** | Doubles as DPDP audit evidence |
| Server | **Uvicorn (dev) + Gunicorn (prod)** | Standard |
| Background jobs | **Celery 5.4 + Redis** | Phase 1 uses it only for delayed lab-OCR placeholder; Phase 2 for WhatsApp dispatch |
| Logging | **structlog** | JSON logs with request_id |
| Linting | **ruff** | Replaces black + isort + flake8 |
| Type checking | **mypy** | Strict mode |
| Tests | **pytest + pytest-asyncio** | |
| Dep mgmt | **Poetry** | |

### Mobile — `vital-mobile` repo (separate from backend)

| Layer | Choice | Notes |
|---|---|---|
| Framework | **Expo (React Native) + TypeScript** | Cross-platform, AI-assisted dev velocity |
| Routing | **expo-router** | File-based |
| Server state | **TanStack Query** | |
| Forms | **react-hook-form + zod** | |
| API types | **openapi-typescript** | Generated from backend `openapi.json`, committed to repo |
| Charts | **Victory Native XL + react-native-skia** | |
| Notifications | **expo-notifications** | Local notifications in Phase 1, push later |
| Icons | **lucide-react-native** | Outline only, 1.5 px |
| Fonts | **Fraunces + Geist Sans + Geist Mono** | self-loaded via expo-font, Google Fonts CDN |

### Phase 1 infrastructure (cheap path — until ~500 active users)

| Component | Choice | Approx ₹/month |
|---|---|---|
| Compute + DB + cache | **Single EC2 t3.small** in ap-south-1, docker-compose with FastAPI + Postgres 16 + Redis 7 | ~₹1,500 |
| TLS | **Caddy** reverse proxy (auto Let's Encrypt) | free |
| Backups | **pg_dump** cron → S3, daily, 30-day retention | ~₹100 |
| Static + DNS | **Cloudflare** free tier | free |
| Push notifications | **Expo's free tier** (local notifications only in Phase 1) | free |
| Object storage | **Cloudflare R2** for non-clinical assets; S3 ap-south-1 for lab reports | ~₹500 |
| Error tracking | **Sentry free tier** | free |
| Uptime | **Better Stack free tier** | free |
| Domain | | ~₹100 |
| **Phase 1 total** | | **~₹3,000–5,000/month** |

### Phase 2 migration (when MRR > ₹50K/month)

Lift-and-shift to ECS Fargate + RDS Multi-AZ + ElastiCache. The docker-compose definitions translate directly to ECS task definitions. **One-day migration**, no code changes.

---

## 3. Database schema (PostgreSQL)

Identical to v1. Drop into Alembic via Prompt 1.

```sql
-- Shared tables (used by wellness + clinic)
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id       TEXT,
  email           TEXT UNIQUE,
  kyros_patient_id TEXT,
  subscription_tier TEXT NOT NULL DEFAULT 'free',
  timezone        TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  actor_type      TEXT NOT NULL,          -- 'user' | 'system' | 'doctor' | 'admin'
  action          TEXT NOT NULL,
  resource_type   TEXT,
  resource_id     UUID,
  payload         JSONB,
  ip_address      TEXT,
  user_agent      TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_user_time ON audit_log(user_id, occurred_at DESC);

-- Wellness domain (prefix wn_)
CREATE TABLE wn_tracked_items (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category        TEXT NOT NULL,
  name            TEXT NOT NULL,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  status          TEXT NOT NULL DEFAULT 'active',
  start_date      DATE NOT NULL,
  end_date        DATE,
  source          TEXT NOT NULL DEFAULT 'manual',
  source_ref      TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_items_user_status ON wn_tracked_items(user_id, status);
CREATE INDEX idx_wn_items_category ON wn_tracked_items(user_id, category);

CREATE TABLE wn_reminders (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tracked_item_id UUID NOT NULL REFERENCES wn_tracked_items(id) ON DELETE CASCADE,
  schedule        JSONB NOT NULL,
  message_template TEXT NOT NULL,
  channels        TEXT[] NOT NULL DEFAULT ARRAY['in_app'],
  active          BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_reminders_active ON wn_reminders(active) WHERE active = true;

CREATE TABLE wn_log_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tracked_item_id UUID NOT NULL REFERENCES wn_tracked_items(id) ON DELETE CASCADE,
  reminder_id     UUID REFERENCES wn_reminders(id) ON DELETE SET NULL,
  fire_key        TEXT,
  action          TEXT NOT NULL,
  value           JSONB NOT NULL DEFAULT '{}'::jsonb,
  note            TEXT,
  occurred_at     TIMESTAMPTZ NOT NULL,
  source          TEXT NOT NULL DEFAULT 'manual',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uniq_wn_log_fire_key ON wn_log_entries(fire_key) WHERE fire_key IS NOT NULL;
CREATE INDEX idx_wn_log_user_time ON wn_log_entries(user_id, occurred_at DESC);

CREATE TABLE wn_measurements (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type            TEXT NOT NULL,
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
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  report_date     DATE NOT NULL,
  lab_name        TEXT,
  file_url        TEXT,
  file_mime       TEXT,
  parsed          JSONB NOT NULL DEFAULT '{}'::jsonb,
  source          TEXT NOT NULL DEFAULT 'manual',
  source_ref      TEXT,
  note            TEXT,
  status          TEXT NOT NULL DEFAULT 'active',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_wn_lab_reports_user_date ON wn_lab_reports(user_id, report_date DESC);
```

### Reminder schedule JSON

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
- `source` and `source_ref` on every domain table — populated as `'manual'` in Phase 1.
- `reminders.channels` as an array — room for `whatsapp`, `voice_call`, `sms`.
- `metadata` and `parsed` as JSONB — Phase 3 AI extraction populates the same shapes humans fill manually.
- `IStorageAdapter` interface — Phase 1 LocalDiskStorage, Phase 2 swaps to S3 ap-south-1.
- The `clinic/` folder in the backend is empty in Phase 1; Phase 2 fills it with consultation, prescription, and lab-order routes that read/write the same database.

---

## 5. Visual design system (the "not AI-coloured" part)

Aesthetic direction: **editorial clinical** — refined, restrained, warm. Like a premium medical journal, not a wellness app shipped from a Lovable template.

**Type stack** (open source, loaded from Google Fonts CDN via `expo-font`):
- Display + large numerals: **Fraunces** (variable serif, optical-size aware)
- Body + UI: **Geist Sans** (regular, medium, semibold)
- Mono / tabular: **Geist Mono**

Avoid Inter, Roboto, SF Pro, generic system fonts.

**Colour tokens:**

```ts
export const tokens = {
  bone:        '#FAF8F4',  // primary background
  paper:       '#FFFFFF',  // card surface
  ink:         '#1A1A1A',  // primary text
  slate:       '#595959',  // secondary text
  mist:        '#8C8C8C',  // tertiary, labels
  hairline:    '#E8E5DD',  // 1px borders
  tealDeep:    '#2D5F5D',  // accent — used sparingly
  positive:    '#3F6B4E',  // muted forest
  warning:     '#B07A1F',  // muted amber
  critical:    '#8B2C1F',  // muted brick
  chartLine:   '#1A1A1A',  // charts default to ink, not colour
} as const;
```

**Layout grammar**
- 8-pt grid (4 / 8 / 12 / 16 / 24 / 32 / 48)
- Hairline borders, not shadows. One subtle shadow on Today cards only.
- Card radius 8 px, button radius 10 px. No pill shapes, no blobs.
- 32 px between sections, 12 px between timeline items.

**Numerical typography**
- Big numbers (weight, BP, HbA1c) in Fraunces 48–64 px, tight leading.
- Unit (`kg`, `mmHg`, `%`) in Geist Sans, smaller, `slate`.
- Trend indicators are typographic, not emoji: `▲ ▼ —` in `positive` / `critical` / `slate`.

**Iconography**: lucide-react-native, outline only, 1.5 px stroke, never filled.

**Banned by default**: purple/pink gradients, glassmorphism, neon cyan, 3D icons, emoji in UI chrome, Tailwind defaults like `bg-blue-500`.

---

## 6. Claude Code prompt queue (FastAPI stack)

Two repos. Run the backend prompts (P0–P5) in `kyros-backend/`, then the mobile prompts (P6–P13) in `vital-mobile/`.

---

### Prompt 0 — Backend repo scaffold (`kyros-backend`)

```
Initialize a new Python project at the current directory for the Kyros backend — a FastAPI application that will serve both the Vital wellness app (Phase 1) and the Kyros clinic platform (Phase 2). Single codebase, separate domain modules.

Create this structure:

  app/
    __init__.py
    main.py                      # FastAPI factory, mounts routers
    config.py                    # Pydantic Settings, loads from env
    database.py                  # async SQLAlchemy engine, sessionmaker, Base
    
    core/                        # Cross-cutting, used by all domains
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
    
    cli.py                       # typer CLI: export-openapi, seed
  
  alembic/
    versions/
    env.py                       # configured for async engine, autogenerate from app.shared.models + app.wellness.models
    script.py.mako
  alembic.ini
  
  tests/
    conftest.py                  # async test client, test DB fixtures
    core/__init__.py
    shared/__init__.py
    wellness/__init__.py
  
  scripts/
    seed.py
  
  pyproject.toml                 # Poetry
  poetry.lock
  .env.example                   # DATABASE_URL, REDIS_URL, STORAGE_DIR, LOG_LEVEL, ENV
  .gitignore
  README.md
  Dockerfile                     # multi-stage, slim base, non-root user
  docker-compose.yml             # postgres 16, redis 7, api with hot reload
  .dockerignore
  Caddyfile                      # reverse proxy config for Phase 1 EC2 deploy (commented placeholder)
  .github/workflows/
    test.yml                     # pytest + ruff + mypy on PR
    deploy.yml                   # ssh + docker compose pull && up on push to main (Phase 1 simple)

Versions:
- Python 3.12
- FastAPI 0.115+
- SQLAlchemy 2.0 (async)
- Alembic 1.13+
- Pydantic v2
- structlog 24.x
- httpx 0.27+
- slowapi
- typer (for CLI)
- pytest + pytest-asyncio + pytest-cov

Tooling:
- Poetry for dependency management
- ruff for lint + format (line length 100, target py312)
- mypy strict mode
- pre-commit hooks for ruff + mypy

docker-compose.yml must bring up postgres 16, redis 7, and the API on localhost:8000 with hot reload via `uvicorn --reload`.

Do NOT add any wellness routes, models, or domain logic yet. Only scaffolding. The wellness/ folder has empty __init__.py files everywhere.

After scaffolding, print the directory tree and the commands to get it booted locally:
  cp .env.example .env
  docker compose up -d postgres redis
  poetry install
  poetry run alembic upgrade head  (will be no-op until P1)
  poetry run uvicorn app.main:app --reload
```

---

### Prompt 1 — SQLAlchemy models + Alembic migrations

```
In app/shared/models/ and app/wellness/models/, define SQLAlchemy 2.0 models for all Phase 1 tables.

Shared models (app/shared/models/):

  users.py — class User(Base):
    __tablename__ = 'users'
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=text('gen_random_uuid()'))
    device_id: Mapped[str | None] = mapped_column(Text, index=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    kyros_patient_id: Mapped[str | None] = mapped_column(Text)
    subscription_tier: Mapped[str] = mapped_column(Text, server_default=text("'free'"))
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'Asia/Kolkata'"))
    created_at, updated_at: Mapped[datetime] (TIMESTAMPTZ, server_default=text('now()'), updated_at also with server_onupdate)

  audit_log.py — class AuditLog(Base):
    Per the schema in section 3. user_id FK with ON DELETE SET NULL.

Wellness models (app/wellness/models/), one file each:

  tracked_item.py — class TrackedItem(Base):
    __tablename__ = 'wn_tracked_items'
    All fields per schema. user_id FK with ON DELETE CASCADE.
    Include Index('idx_wn_items_user_status', 'user_id', 'status').
    Relationship: reminders = relationship('Reminder', back_populates='tracked_item', cascade='all, delete-orphan')
  
  reminder.py — class Reminder(Base):
    __tablename__ = 'wn_reminders'
    schedule: Mapped[dict] = mapped_column(JSONB)
    channels: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("ARRAY['in_app']"))
    active: Mapped[bool], default true.
    Relationship: tracked_item = relationship('TrackedItem', back_populates='reminders')
  
  log_entry.py — class LogEntry(Base):
    __tablename__ = 'wn_log_entries'
    fire_key: Mapped[str | None] = mapped_column(Text)
    Partial unique index: Index('uniq_wn_log_fire_key', 'fire_key', unique=True, postgresql_where=text('fire_key IS NOT NULL'))
    reminder_id FK with ON DELETE SET NULL.
  
  measurement.py — class Measurement(Base):
    __tablename__ = 'wn_measurements'
    value: Mapped[Decimal] = mapped_column(Numeric)
    Index on (user_id, type, measured_at DESC).
  
  lab_report.py — class LabReport(Base):
    __tablename__ = 'wn_lab_reports'
    parsed: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str], default 'active' (for soft delete).

Requirements:
- All models inherit from Base in app/database.py
- All UUID PKs use server_default=text('gen_random_uuid()')
- All TIMESTAMPTZ columns use server_default=text('now()'), updated_at columns also use server_onupdate
- All FK cascades exactly as specified in the schema
- All indexes defined as Index() at module level
- Use Mapped[] type annotations throughout (SQLAlchemy 2.0 typed style)
- Add __repr__ to each model
- Export all models from app/shared/models/__init__.py and app/wellness/models/__init__.py for Alembic autogenerate

Configure Alembic:
- alembic/env.py imports target_metadata = Base.metadata
- Imports all models so autogenerate sees them
- Configured for async engine

Then:
1. Run `alembic revision --autogenerate -m "initial wellness schema"`
2. Inspect the generated SQL — must match section 3 of the build spec
3. Run `alembic upgrade head` against docker-compose postgres
4. Write scripts/seed.py that creates: 1 guest user, 1 medication tracked item with a recurring twice-daily reminder, 1 water tracked item with a 2-hour interval reminder, 1 workout tracked item with a 3-day-a-week reminder

Tests in tests/wellness/test_models.py:
- Save and fetch each model
- Cascade delete: deleting User deletes wn_tracked_items, deletes wn_reminders, deletes wn_log_entries
- Reminder deletion sets log_entry.reminder_id to NULL (not cascade)
- Unique fire_key: inserting the same fire_key twice raises IntegrityError

After completion: print the generated migration SQL and the seed script output.
```

---

### Prompt 2 — Pydantic schemas + core utilities

```
Build the Pydantic schemas and core utilities.

In app/wellness/schemas/, one file each:

schedule.py:
  RecurringSchedule(BaseModel):
    type: Literal['recurring']
    times: list[str]  # validator: each matches r'^([01]\d|2[0-3]):[0-5]\d$'
    days_of_week: list[Literal['mon','tue','wed','thu','fri','sat','sun']]  # non-empty
    start_date: date
    end_date: date | None = None
    timezone: str  # validator: must be a valid IANA timezone via zoneinfo

  IntervalSchedule(BaseModel):
    type: Literal['interval']
    interval_minutes: int  # gt=0, le=1440
    active_window: dict  # {'start': 'HH:MM', 'end': 'HH:MM'}, validator: end > start
    days_of_week: list[Literal['mon','tue','wed','thu','fri','sat','sun']]
    timezone: str

  Schedule = Annotated[Union[RecurringSchedule, IntervalSchedule], Field(discriminator='type')]

  def expand_schedule(schedule: Schedule, from_dt: datetime, to_dt: datetime) -> list[datetime]:
    """
    Return timezone-aware datetimes (in schedule.timezone) when the reminder
    should fire, within [from_dt, to_dt) inclusive of from, exclusive of to.
    
    Recurring: iterate each date in range, each time in times,
               filter by days_of_week.
    Interval: iterate from from_dt by interval_minutes,
              filter by active_window and days_of_week.
    
    Uses zoneinfo (stdlib) for DST safety.
    Returns sorted ascending.
    """

tracked_item.py:
  Category = Literal['medication','water','meal','workout','vital_check','custom']
  Source = Literal['manual','kyros','ai_extracted']
  Status = Literal['active','paused','discontinued']
  
  MedicationMeta(BaseModel): drug_name: str, dosage: str, form: Literal['tablet','capsule','syrup','injection','other'], with_food: bool = False, instructions: str | None = None
  WaterMeta(BaseModel): daily_target_ml: int, glass_size_ml: int = 250
  WorkoutMeta(BaseModel): workout_type: str, duration_minutes: int, location: str | None = None
  MealMeta(BaseModel): meal_name: str, notes: str | None = None
  CustomMeta(BaseModel): title: str, notes: str | None = None
  
  TrackedItemBase(BaseModel): category, name, metadata: dict (validated against the per-category schema at the route level)
  TrackedItemRead(TrackedItemBase): id, user_id, status, start_date, end_date, source, source_ref, created_at, updated_at, reminders: list[ReminderRead] (forward ref)
  TrackedItemCreate(BaseModel): category, name, metadata, start_date, end_date | None
  TrackedItemUpdate(BaseModel): all fields optional

reminder.py:
  ReminderRead(BaseModel): id, tracked_item_id, schedule (Schedule), message_template, channels, active, created_at, updated_at
  ReminderCreate(BaseModel): schedule (Schedule), message_template, channels: list[str] = ['in_app']
  ReminderUpdate: all optional
  
  UpcomingFire(BaseModel):
    reminder_id: UUID
    tracked_item_id: UUID
    fire_at: datetime  # tz-aware
    fire_key: str  # f'{reminder_id}:{fire_at.isoformat()}'
    payload: dict  # {title, body, category, actions: list[str]}

log_entry.py:
  LogAction = Literal['taken','skipped','snoozed','logged_value','acknowledged']
  LogEntryRead, LogEntryCreate (with optional fire_key, optional reminder_id, optional value, optional note)

measurement.py:
  MeasurementType = Literal['weight','bp_systolic','bp_diastolic','heart_rate','fasting_glucose','hba1c','body_temp','steps']
  MeasurementRead, MeasurementCreate, MeasurementUpdate

lab_report.py:
  ParsedTest(BaseModel): name, value (str — keeps "Negative" works), unit, ref_low: float | None, ref_high: float | None, flag: Literal['normal','low','high','critical']
  LabReportRead, LabReportCreate, LabReportUpdate

In app/core/:

storage.py:
  class IStorageAdapter(Protocol):
    async def save(self, content: bytes, key: str, mime_type: str) -> str: ...
    async def read(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str: ...
  
  class LocalDiskStorage(IStorageAdapter):
    base_dir from STORAGE_DIR env. signed_url returns a path with HMAC token (SIGNING_SECRET env).
  
  def get_storage() -> IStorageAdapter:
    factory that reads STORAGE_BACKEND env (local in Phase 1)

audit.py:
  Middleware that on every successful POST/PATCH/DELETE writes an audit_log row.
  Fields: user_id (from request.state.user), actor_type='user', action=request.url.path,
  resource_type extracted from path, resource_id from response body if present, ip_address, user_agent, payload=request body (PII-scrubbed).

auth.py:
  async def get_current_user(request: Request, db: AsyncSession) -> User:
    Read X-Device-Id header (required, raise 401 if missing).
    Validate format (16-64 chars, alphanumeric + dashes).
    Query users by device_id. If exists, return.
    If not, INSERT with ON CONFLICT (device_id) DO NOTHING RETURNING, then re-fetch.
    Store user on request.state for the audit middleware.

rate_limit.py:
  slowapi Limiter keyed on request.state.user.id if present else IP.
  Default limits: 60/minute per user, 10/minute on lab-report POST.

logging.py:
  structlog config: JSON in prod, console-pretty in dev.
  Add request_id (uuid4) as a contextvar populated by a middleware.

exceptions.py:
  NotFoundError, ForbiddenError, ValidationError (separate from Pydantic's), RateLimitError, ConflictError.
  Handlers return: { error: { code, message, request_id, details? } } with appropriate status codes.

Tests:
  tests/wellness/schemas/test_schedule.py:
    - expand_schedule recurring 8am+8pm IST over 48h → 4 events at correct local times
    - expand_schedule interval 2h, 8-22, weekdays only, over 24h on a Monday → ~8 events
    - expand_schedule across an Asia/Kolkata day boundary
    - expand_schedule across a US/Eastern DST boundary → no missing/duplicate fires
    - end_date respected
    - empty days_of_week → ValidationError on construction
  
  tests/core/test_storage.py:
    - LocalDiskStorage save → read → delete roundtrip
    - signed_url contains a valid HMAC, expires after TTL
  
  tests/core/test_auth.py:
    - Missing X-Device-Id → 401
    - New device_id → creates user
    - Same device_id twice → returns same user (no race condition)
  
  tests/core/test_audit.py:
    - POST request writes one audit_log row with correct fields

After completion: run pytest with coverage, target ≥80% on core/ and schemas/.
```

---

### Prompt 3 — API foundations + OpenAPI export

```
Wire up the FastAPI app and shared routes.

app/main.py:
  def create_app() -> FastAPI:
    app = FastAPI(
      title='Kyros Backend',
      version='0.1.0',
      description='Wellness (Phase 1) + Clinic (Phase 2)',
      docs_url='/docs' if config.ENV != 'production' else None,
    )
    Register middleware in order: request_id → logging → CORS → audit → rate_limit
    Register exception handlers from core/exceptions
    Mount routers (each module exports `router`):
      app.shared.routes.health         → /health
      app.shared.routes.users          → /v1/users
      # wellness and clinic mounts come in P4-P5
    Add OpenAPI tag groups: 'Health', 'Users', 'Wellness', 'Clinic'
    Customize OpenAPI schema generation to include X-Device-Id as a required global header
  
  app = create_app()

app/shared/routes/health.py:
  router = APIRouter(tags=['Health'])
  
  GET /health → {
    status: 'ok',
    version: str,
    env: str,
    db: 'reachable' | 'unreachable',
    storage: 'reachable' | 'unreachable'
  }
  
  Lightly pings DB (SELECT 1) and storage.signed_url('healthcheck') to verify both.

app/shared/routes/users.py:
  router = APIRouter(prefix='/v1/users', tags=['Users'])
  
  POST /guest
    No auth — but requires X-Device-Id header.
    Idempotent: returns existing user for that device_id, or creates one.
    Returns: UserRead schema.
  
  GET /me
    Depends(get_current_user)
    Returns: UserRead.
  
  PATCH /me
    Depends(get_current_user)
    Body: optional email, timezone, subscription_tier (admin-only — reject for now)
    Returns: UserRead.

CLI in app/cli.py (typer):
  $ python -m app.cli export-openapi --output openapi.json
    Generates and writes the OpenAPI schema to disk.
    This is what vital-mobile consumes for typegen.
  
  $ python -m app.cli seed
    Runs scripts/seed.py.

Tests:
  tests/conftest.py:
    - Async test client fixture
    - Test DB fixture: creates a fresh schema per test session, drops after
    - Async session fixture with rollback per test
    - Sample User fixture
  
  tests/shared/test_health.py:
    - GET /health returns 200 with status='ok', db='reachable'
  
  tests/shared/test_users.py:
    - POST /v1/users/guest with new device_id → 201, returns user with that device_id
    - POST /v1/users/guest with same device_id → 200 (or 201), returns the same user.id
    - GET /v1/users/me with valid X-Device-Id → 200, returns user
    - GET /v1/users/me without X-Device-Id → 401

After completion:
  - Run docker compose up
  - curl http://localhost:8000/health → verify 200
  - curl -X POST -H 'X-Device-Id: test-device-abc123' http://localhost:8000/v1/users/guest → verify user creation
  - Run again with same header → verify idempotent
  - Open http://localhost:8000/docs and verify OpenAPI UI renders
  - Run `python -m app.cli export-openapi --output openapi.json` and verify openapi.json is created
  - Commit openapi.json to the repo
```

---

### Prompt 4 — Wellness API: tracked items + reminders + upcoming fires

```
Build the wellness domain routes for tracked items and reminders.

In app/wellness/routes/tracked_items.py:
  router = APIRouter(prefix='/v1/wellness/tracked-items', tags=['Wellness'])
  All endpoints depend on get_current_user.
  
  GET    /                          ?category=&status=  → list user's items with embedded reminders
  POST   /                          body: TrackedItemCreate → create
  GET    /{item_id}                 → read with embedded reminders[]
  PATCH  /{item_id}                 body: TrackedItemUpdate → partial update
  DELETE /{item_id}                 → soft delete: status='discontinued', deactivate all child reminders
  
  GET    /{item_id}/reminders       → list reminders for the item
  POST   /{item_id}/reminders       body: ReminderCreate → create reminder

In app/wellness/routes/reminders.py:
  router = APIRouter(prefix='/v1/wellness/reminders', tags=['Wellness'])
  
  PATCH  /{reminder_id}             body: ReminderUpdate → partial update
  DELETE /{reminder_id}             → set active=false (soft delete)
  
  GET    /upcoming                  ?hours=24 (default 24, max 168) → list[UpcomingFire]

In app/wellness/services/upcoming.py:
  async def compute_upcoming(user_id: UUID, hours: int, db: AsyncSession) -> list[UpcomingFire]:
    1. Fetch all active reminders joined with their tracked_items where:
       - tracked_item.user_id = user_id
       - tracked_item.status = 'active'
       - reminder.active = true
       - tracked_item.start_date <= today AND (end_date IS NULL OR end_date >= today)
    2. For each reminder, call expand_schedule(reminder.schedule, now, now+hours)
    3. For each fire timestamp, build UpcomingFire:
       - fire_key = f'{reminder.id}:{fire_at.isoformat()}'
       - payload.title: derived from tracked_item.category ('Medication', 'Hydration', 'Workout', 'Meal', 'Reminder')
       - payload.body: render reminder.message_template with tracked_item.metadata as context
         (use simple {key} substitution via str.format_map(SafeDict) — missing keys render as the literal key, never crash)
       - payload.category: tracked_item.category
       - payload.actions: category-specific list:
           medication → ['taken','skipped','snooze_15']
           water → ['logged_value','skipped','snooze_15']
           meal → ['taken','skipped','snooze_15']
           workout → ['taken','skipped','snooze_30']
           vital_check → ['logged_value','skipped','snooze_15']
           custom → ['acknowledged','snooze_15']
    4. Sort ascending by fire_at, return.

Mount routers in app/main.py.

Requirements:
- All routes use Pydantic schemas from app/wellness/schemas
- Authorization: query filters always include user_id = current_user.id; cross-user access returns 404 (not 403, don't leak existence)
- TrackedItemCreate validates metadata against the per-category schema (use a discriminated union via category field)
- Soft delete cascade: DELETE on tracked_item sets status='discontinued' AND active=false on all child reminders, in one transaction
- All mutating endpoints flow through the audit middleware automatically (already wired in P2)

Tests in tests/wellness/routes/:
  test_tracked_items.py:
    - Full CRUD lifecycle for medication
    - Cross-user isolation: user A creates item, user B GETs it → 404
    - Soft delete: tracked_item status changes, child reminders deactivated, item still readable
    - Invalid metadata (wrong category shape) → 422 with field-level errors
  
  test_reminders.py:
    - Create/update/delete reminder
    - Schedule validation: invalid timezone, end before start → 422
    - Soft delete sets active=false, reminder still readable
  
  test_upcoming.py:
    - Recurring twice-daily medication → 4 events over 48h
    - Interval water every 2h, 8-22, weekdays → ~8 events on a weekday, 0 on a Sunday-only off day
    - Template substitution: {drug_name} replaced from metadata; missing {foo} renders as 'foo' literal
    - DST boundary test using US/Eastern → no double-fires, no missing fires
    - Inactive reminder excluded
    - Discontinued tracked_item excluded
    - Cross-user reminder excluded
    - hours=24 returns subset of hours=48

Update the OpenAPI export:
  Run `python -m app.cli export-openapi --output openapi.json` and commit.

After completion: integration test via curl —
  1. Create medication via POST
  2. Create twice-daily reminder
  3. GET /upcoming?hours=48
  4. Verify 4 fire events with correctly substituted bodies and category-appropriate actions
```

---

### Prompt 5 — Wellness API: logs + measurements + lab reports

```
Build the remaining wellness routes.

In app/wellness/routes/logs.py:
  router = APIRouter(prefix='/v1/wellness/logs', tags=['Wellness'])
  
  POST /
    Body: LogEntryCreate { tracked_item_id, action, reminder_id?, fire_key?, value?, note?, occurred_at }
    If fire_key provided and a log already exists with that fire_key for this user:
      Return the existing log row with HTTP 200 (idempotent, not 409).
    Else: insert and return 201.
    Implementation: use INSERT ... ON CONFLICT (fire_key) DO NOTHING RETURNING *, 
                    then if no row returned, re-fetch the existing one.
  
  GET /
    Query: ?from=&to=&tracked_item_id=&action=
    Returns paginated (cursor-based, default limit 50, max 200), newest first.

In app/wellness/routes/measurements.py:
  router = APIRouter(prefix='/v1/wellness/measurements', tags=['Wellness'])
  
  POST   /                              create
  GET    /                              ?type=&from=&to=, paginated, newest first
  GET    /{id}                          read
  PATCH  /{id}                          partial update
  DELETE /{id}                          hard delete (these are user-corrected, not adherence history)

In app/wellness/routes/lab_reports.py:
  router = APIRouter(prefix='/v1/wellness/lab-reports', tags=['Wellness'])
  
  POST   /                              multipart upload:
    file: UploadFile (max 10 MB; accept image/jpeg, image/png, application/pdf)
    metadata: JSON form field containing report_date, lab_name, parsed: list[ParsedTest], note
    
    Implementation:
      1. Read file bytes, validate size and mime
      2. Generate storage key: f'user-{user.id}/labs/{uuid4()}-{secure_filename(file.filename)}'
      3. await storage.save(content, key, mime_type)
      4. Insert lab_report row with file_url=key, file_mime, parsed
      5. Return LabReportRead with signed URL for file
  
  GET    /                              list, newest first, paginated
  GET    /{id}                          detail with fresh signed URL
  GET    /{id}/file                     verifies access, then returns streaming response from storage.read()
  PATCH  /{id}                          edit metadata or parsed JSON (NOT the file)
  DELETE /{id}                          soft delete: set status='deleted', keep the file (cleanup job later)

Mount routers in app/main.py.

Requirements:
- Log entry idempotency at DB level via the partial unique index on fire_key
  Handle the rare race condition (two simultaneous POSTs with same fire_key): catch IntegrityError, re-query, return existing
- Lab report POST is rate-limited (10/min per user — covered by core/rate_limit.py)
- File access: GET /{id}/file checks the lab_report row belongs to current_user before storage.read()
- Never call open() or pathlib directly in route code — always through IStorageAdapter
- DELETE on lab_report does NOT call storage.delete() immediately — soft delete only; a future cleanup job will sweep

Tests in tests/wellness/routes/:
  test_logs.py:
    - POST with new fire_key → 201
    - POST with same fire_key → 200, same row returned
    - Race condition simulation: two concurrent POSTs with same fire_key → both return the same row, no duplicate
    - Filtering by tracked_item_id, action, date range
    - Cross-user log retrieval → 404
  
  test_measurements.py:
    - CRUD lifecycle
    - Type filtering: ?type=weight returns only weight rows
    - Time-range query: from-to inclusive
  
  test_lab_reports.py:
    - Upload PDF → 201, returns signed URL
    - Upload over 10 MB → 413
    - Upload wrong mime → 415
    - GET /{id}/file with valid auth → 200, content matches
    - GET /{id}/file with another user's auth → 404
    - PATCH parsed JSON, GET → reflects change
    - DELETE → status='deleted', GET /{id} → 404 (or returns with deleted flag based on chosen policy — pick one and document)

Update the OpenAPI export and commit openapi.json.

After completion: full integration test via curl —
  1. Create medication and reminder (from P4)
  2. GET /upcoming?hours=24, pick the first UpcomingFire
  3. POST /logs with action='taken' and the fire_key from step 2 → 201
  4. POST same again → 200, same row
  5. POST /measurements: weight=72.4 kg → 201
  6. POST /lab-reports: upload a sample PDF + parsed tests → 201
  7. GET /lab-reports/{id}/file → file streams back
```

---

### Prompt 6 — Mobile repo scaffold + OpenAPI typegen + design system

```
Initialize a NEW git repository at the current directory (NOT inside kyros-backend — this is a sibling repo) called vital-mobile.

This is the Phase 1 standalone wellness app. Brand: Vital. Separate deploy lifecycle from the backend.

Start with: `npx create-expo-app@latest . --template blank-typescript`
Then add expo-router.

Structure to set up:

  app/                              # expo-router file-based routes
    _layout.tsx                     # root: ThemeProvider, QueryClientProvider, font loader
    (tabs)/
      _layout.tsx                   # bottom tabs config
      index.tsx                     # Today
      library.tsx
      insights.tsx
      settings.tsx
    item/
      [id].tsx                      # tracked item detail
      new.tsx                       # category picker
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
    onboarding.tsx
  
  src/
    api/
      client.ts                     # fetch wrapper with X-Device-Id from expo-secure-store
      generated/
        schema.ts                   # openapi-typescript output — COMMITTED to repo
      queries.ts                    # TanStack Query hooks using generated types
    theme/
      tokens.ts                     # exact colour/type/spacing/radii per build spec
      typography.ts                 # text style presets
      ThemeProvider.tsx             # React context
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
    notifications/                  # placeholder for P10
      .gitkeep
    schedule/                       # placeholder for P9
      .gitkeep
    hooks/
    utils/
  
  scripts/
    sync-types.ts                   # downloads openapi.json from backend, runs openapi-typescript
  
  .env.example                      # EXPO_PUBLIC_API_URL, EXPO_PUBLIC_ENV
  app.json                          # expo config: name='Vital', slug, ios.bundleId, android.package, plugins
  package.json
  tsconfig.json                     # strict mode
  README.md
  .gitignore
  eas.json                          # EAS Build config for production builds (basic placeholder)

Dependencies (pnpm preferred but npm OK):
- expo-router, expo-font, expo-secure-store, expo-image-picker, expo-document-picker, expo-notifications, expo-haptics, expo-linking
- @tanstack/react-query@5
- react-hook-form, @hookform/resolvers, zod
- date-fns, date-fns-tz
- victory-native, react-native-skia
- lucide-react-native, react-native-svg
- openapi-typescript (dev dep)
- @testing-library/react-native, jest-expo, @types/jest (dev)

OpenAPI typegen workflow:
- scripts/sync-types.ts:
    1. Fetch openapi.json from process.env.OPENAPI_URL || 'http://localhost:8000/openapi.json'
       OR read from a local path: ../kyros-backend/openapi.json
    2. Pipe through openapi-typescript → src/api/generated/schema.ts
    3. Add a generated banner comment with timestamp
- package.json script: "sync:types": "tsx scripts/sync-types.ts"
- README note: "After backend changes, run `pnpm sync:types` and commit the diff"

API client (src/api/client.ts):
- Stores device_id in expo-secure-store, generates uuid v4 on first run
- Reusable fetch wrapper:
    - Base URL from EXPO_PUBLIC_API_URL
    - Adds X-Device-Id header automatically
    - JSON Content-Type by default
    - Handles 4xx (throw with parsed error body), 5xx (throw with generic message)
    - Supports multipart for file uploads (used by lab-reports POST)
- Type-safe with the generated schema:
    Use openapi-fetch (the companion to openapi-typescript) so request/response are inferred from the OpenAPI spec.

Theme system (src/theme/tokens.ts):
  Export all tokens EXACTLY as specified in section 5 of the build spec:
  - colours (bone, paper, ink, slate, mist, hairline, tealDeep, positive, warning, critical, chartLine)
  - spacing (s4, s8, s12, s16, s24, s32, s48)
  - radii (card: 8, button: 10)
  - typography presets (displayXL, displayL, displayM, h1, h2, body, bodySmall, caption, label, mono) with fontFamily, fontSize, lineHeight, letterSpacing

Font loading:
- In app/_layout.tsx, use useFonts from expo-font to load:
  - Fraunces (variable from Google Fonts CDN)
  - Geist Sans (400, 500, 600)
  - Geist Mono (400, 500)
- Show a blank loading screen until fonts are ready (do NOT render the app)
- Falls back to system fonts only if loading fails after 5s timeout

Component primitives (src/components/):
  Each accepts a typography preset prop where text is involved, and uses theme tokens — never inline hex.
  - Screen: SafeAreaView with bone background, padding presets
  - Card: paper surface, 1px hairline border, 8 radius. Optional `elevated` prop adds a subtle shadow.
  - Text: variant prop maps to typography preset; color prop maps to a token name
  - Button: variants 'primary' (tealDeep fill, paper text), 'secondary' (hairline border, ink text), 'ghost' (no border, slate text). Sizes sm | md | lg.
  - ListItem: left slot (icon), title + subtitle (Text), right slot (chevron / status), tappable with subtle press state
  - Sparkline: single-colour SVG line via react-native-svg, no axes, no fill, configurable stroke + width
  - Input: bordered, focused state changes border to ink, error state to critical
  - Select: similar to Input but with a chevron and a bottom sheet for options
  - TimePicker: wraps @react-native-community/datetimepicker, outputs "HH:mm" strings
  - DayOfWeekPicker: 7 toggleable pills (first letter of weekday in mono)
  - StatusBadge: small uppercase label, colour by variant (positive/warning/critical/neutral)
  - EmptyState: centred title + body + optional CTA, no illustration

Bottom tabs (app/(tabs)/_layout.tsx):
- 4 tabs: Today (Home icon), Library (Layers), Insights (LineChart), Settings (Settings)
- Hairline top border (1px hairline colour)
- bone background
- Active: ink. Inactive: mist. No badge bubbles in Phase 1.

All 4 tab screens render EmptyState placeholders for now — real implementations come in subsequent prompts.

Tests (tests/):
- jest-expo configured
- Smoke test per primitive: renders without crashing, accepts theme tokens, snapshot

After completion:
- Run `pnpm sync:types` (with backend running)
- Run `pnpm ios` or `pnpm android`
- Screenshot the empty Today screen showing Fraunces typography and the tab bar
- Verify openapi-typescript generated correct types in src/api/generated/schema.ts
```

---

### Prompt 7 — Today dashboard

```
Implement the Today screen at app/(tabs)/index.tsx in apps/mobile.
 
Layout, top to bottom:
1. Header row
   - Greeting in Fraunces displayM ("Good morning" / "Good afternoon" / "Good evening" based on local time)
   - Date below in Geist Mono caption, --slate ("Wednesday, 20 May")
   - Settings icon top-right (lucide Settings, --slate)
 
2. Today section
   - Section label "TODAY" in caption, uppercase, letter-spaced, --mist
   - Vertical timeline of upcoming reminders for the next 18 hours, fetched from GET /reminders/upcoming?hours=18
   - Each item: time on left (Geist Mono, --slate), title + subtitle in middle, status/action on right
     - Subtitle examples: "Metformin 500mg · with food", "Glass of water · 250 ml", "Strength workout · 45 min"
   - Items past their fire time and not yet logged: title in --ink, time in --warning
   - Items already logged: title in --slate strikethrough, time in --slate
   - Tap an item → opens a bottom sheet with [Taken] [Skipped] [Snooze 15m] actions
   - Tapping an action calls POST /logs with the right fire_key for dedupe, then optimistically updates the UI via TanStack Query
 
3. Recent measurements section
   - Section label "RECENT"
   - Up to 3 Sparkline cards horizontally scrollable
   - Each card: type name in label uppercase, latest value in Fraunces displayL with unit in body --slate, 14-day sparkline below, trend indicator (▲/▼/—) with delta vs 30-day average
   - Tap → measurement type detail screen (stub for now, just a route)
 
4. This week section
   - Section label "THIS WEEK"
   - 2–3 plain text status lines, no charts
   - Examples: "5 of 7 days on water goal", "BP stable across 4 readings", "No missed medications"
   - These are computed locally from logs/measurements queries — Phase 1 dumb-aggregations, not AI
 
5. Empty states
   - No reminders today → EmptyState with title "Nothing scheduled for today", subtitle "Add your first reminder from the Library tab", small ghost button "Open Library"
   - No measurements yet → suppress section entirely
   - No data for This week → suppress section entirely
 
Spacing: 24 px between sections, 12 px between timeline items.
 
After completion: seed the dev API with a medication (2x daily), a water target, and 5 weight measurements over 14 days. Verify the Today screen renders all three sections correctly.
```
 
---

### Prompt 8 — Library + tracked item CRUD UI

```
Implement the Library tab and the tracked-item create/edit flows.
 
Library screen at app/(tabs)/library.tsx:
- Header: "Library" in Fraunces displayM, plus icon top-right linking to /item/new
- Filter chips row: All, Medication, Water, Meals, Workout, Vitals, Custom (--ink active, --slate inactive, hairline borders, no fills)
- Sectioned list grouped by category:
  - Section header in label caption uppercase --mist
  - Each row uses ListItem: category icon left, name + subtitle (e.g. "Metformin 500mg · 2x daily"), --mist chevron right
  - Tap → /item/[id]
- Empty state if no items: "No tracked items yet", body "Add medications, water goals, workouts, and more.", primary button "Add your first item"
 
Category picker screen at app/item/new.tsx:
- Vertical list of 6 large cards, one per category, each with icon + name + one-line description
- Tap → /item/new/medication, /item/new/water, etc. (sub-routes for each form)
 
Per-category create forms (one screen each):
- Medication form fields:
  - drug_name (text, required)
  - dosage (text, e.g. "500 mg", required)
  - form (segmented: tablet / capsule / syrup / injection / other)
  - times_per_day (number stepper 1–6)
  - specific_times[] (TimePicker per dose, defaults spread across waking hours)
  - days_of_week (DayOfWeekPicker, default all)
  - with_food (toggle)
  - start_date (date picker, default today)
  - end_date (optional, "Ongoing" toggle)
  - instructions (multiline, optional)
- Water form:
  - daily_target_ml (number, default 2500)
  - reminder_interval_minutes (number, default 120)
  - active_window start/end (TimePicker, default 08:00–22:00)
- Workout form:
  - workout_type (text)
  - duration_minutes (number)
  - days_of_week (DayOfWeekPicker)
  - time_of_day (TimePicker)
  - location (text, optional)
- Meal form:
  - meal_name (text, e.g. "Breakfast")
  - time (TimePicker)
  - days_of_week (DayOfWeekPicker)
  - notes (multiline, optional)
- Custom form:
  - title, message, schedule (full schedule builder with both recurring and interval modes)
 
On save, each form POSTs to:
- /tracked-items (the item itself, metadata populated from form fields)
- /tracked-items/:id/reminders (one reminder with the corresponding schedule JSON and a message_template using the right placeholders)
 
Then navigates back to Library.
 
Tracked item detail at app/item/[id].tsx:
- Header: item name in displayM, category badge below
- "Reminders" section: list of attached reminders with their schedule summary in plain English ("Daily at 8:00 AM and 8:00 PM")
- "Recent activity" section: last 10 log entries, each row showing time + action
- "Adherence (last 30 days)" stat: simple percentage from logs vs expected fires
- Buttons: Edit (opens the same form prefilled), Pause/Resume (toggles status), Discontinue (soft delete with confirm)
 
Forms use react-hook-form with Zod resolvers, importing schemas from packages/types.
 
After completion: create one item of each category through the UI and verify they appear in the Library list and on Today.
```
 
---

### Prompt 9 — Reminder builder and schedule UI primitives

```
Build the reusable reminder schedule builder used by all category forms.
 
Components in src/components/schedule/:
- ScheduleBuilder.tsx — top-level component, takes a value/onChange schedule JSON. Has a segmented control at the top: "At specific times" / "Every few hours". Renders RecurringBuilder or IntervalBuilder.
- RecurringBuilder.tsx — manages times[] with add/remove rows, each row uses TimePicker; below, DayOfWeekPicker; below, optional date range (start_date / end_date with "Ongoing" toggle)
- IntervalBuilder.tsx — number input for interval_minutes (with helpful labels "Every 1h", "Every 2h"), then active_window start/end TimePickers, then DayOfWeekPicker
- TimePicker.tsx — wraps @react-native-community/datetimepicker; outputs "HH:mm" strings
- DayOfWeekPicker.tsx — 7 toggleable pills, each shows first letter of weekday in Geist Mono; selected = --ink fill + paper text, unselected = hairline border + --slate text
 
ScheduleBuilder must:
- Default timezone to the user's device timezone, stored in the schedule JSON
- Validate using scheduleSchema from packages/types on blur
- Show inline error text (--critical) under the field if invalid
- Emit a schedule JSON that round-trips through scheduleSchema.parse() without loss
 
Integrate ScheduleBuilder into the Custom form. For the other category forms, keep their tailored inputs but have the submit handler construct the equivalent schedule JSON internally — users don't see the full builder for medication/water/workout/meal, just the category-friendly fields.
 
Add Vitest tests in src/components/schedule/__tests__:
- Recurring schedule output matches expected JSON for "8am and 8pm every day"
- Interval schedule output matches expected JSON for "every 2 hours, 8am–10pm, weekdays only"
- Invalid schedule (end time before start time) shows inline error
 
After completion: open the Custom form, build a schedule that fires every 90 minutes between 9 and 6 on weekdays only, save it, and verify the upcoming reminders endpoint expands it correctly for a 48-hour window.
```
 
---

### Prompt 10 — Local notification engine

```
Wire up local notifications in apps/mobile using expo-notifications.
 
Files:
- src/notifications/permissions.ts — requestPermissions(), returns granted/denied
- src/notifications/scheduler.ts   — sync() function: fetches /reminders/upcoming?hours=72, diffs against currently scheduled local notifications, cancels obsolete ones, schedules new ones. Each scheduled notification carries identifier = fire_key.
- src/notifications/handlers.ts    — Notification action handler: when user taps "Taken" / "Skipped" / "Snooze 15m" on a notification, POSTs the corresponding log entry with the fire_key from the notification data. Snooze creates a one-off local notification 15 minutes out.
- src/notifications/categories.ts  — registers a notification category "MEDICATION" with three action buttons: Taken (foreground), Skipped (background), Snooze (background). Similarly "WATER", "WORKOUT", "MEAL" with appropriate actions.
 
Behavior:
- On app foreground, scheduler.sync() runs once
- On any tracked_item or reminder mutation, scheduler.sync() re-runs (invalidate + refetch + reschedule)
- On notification permission denied, surface a non-blocking banner on Today that links to Settings → Notifications
- Snooze 15m: schedule local notif at now+15min with same payload, no API call required (log goes through when user actually taps Taken)
 
Edge cases to handle in code:
- App killed: local notifications still fire (this is the point of local, not push)
- Timezone change: scheduler.sync() detects via device API and re-syncs
- DST: handled by expandSchedule in packages/types (already tested there)
- Notification permission revoked between sessions: detected on foreground, banner shown
 
Settings tab additions:
- Toggle: Notification permissions (deep links to OS settings if denied)
- Toggle: Notification sound on/off
- Timezone display (read-only, computed from device)
 
After completion: create a medication with a reminder 2 minutes in the future, lock the device, wait for the notification to fire, tap "Taken" from the lock screen, then verify the log entry appears on Today.
```
 
---

### Prompt 11 — Measurements + charts

```
Implement the measurements feature.
 
Screens:
- app/measurement/new.tsx — form
  - Type select (weight, BP systolic, BP diastolic, heart rate, fasting glucose, HbA1c, body temp, steps). For BP, render systolic + diastolic as a single form that creates two measurement rows linked by measured_at.
  - Value input (numeric keypad)
  - Unit auto-set per type (kg / mmHg / bpm / mg/dL / % / °C / count) but editable
  - measured_at datetime, defaults to now
  - Optional note
  - Submit → POST /measurements
 
- app/measurement/[type].tsx — detail/trend screen
  - Header: type name in displayM, latest value in displayXL Fraunces with unit in body --slate, trend indicator vs 30-day average
  - Time range chips: 7d / 30d / 90d / 1y / All (--ink active)
  - Chart: Victory Native XL line chart, --chart-line stroke at 1.5 px, no fill, hairline x-axis only, no y-axis line, y-axis labels in mono --slate
  - Reference range band rendered as a translucent --hairline horizontal stripe behind the line if reference_range is present
  - Below chart: list of individual measurements with edit / delete swipe actions
  - For BP, the chart renders two lines (systolic --ink, diastolic --slate)
 
Wire the Today screen's "RECENT" sparkline cards to deep-link into /measurement/[type] on tap.
 
Add chart utilities in src/charts/:
- formatValue(type, value) — returns formatted string with unit
- trendDirection(values) — returns 'up' | 'down' | 'flat' with a delta percentage
- mergeBPRows(measurements) — pairs systolic + diastolic by measured_at
 
After completion: enter 30 days of weight measurements (small fluctuations), view the 30d chart, verify the trend indicator and reference range render. Enter 10 BP readings, verify both lines render.
```
 
---

### Prompt 12 — Lab reports

```
Implement lab report capture and viewing.
 
Screens:
- app/lab/new.tsx
  - Camera / Gallery / PDF picker at top (use expo-image-picker + expo-document-picker). Preview thumbnail once selected.
  - report_date (date picker, defaults today)
  - lab_name (text, optional)
  - Tests array (manually entered in Phase 1):
    - Each test row: name (text), value (text — keep as string so "Negative" works), unit (text), reference low (numeric, optional), reference high (numeric, optional), flag (none / low / high / critical — manual select)
    - "Add another test" button at the bottom
  - Note (multiline, optional)
  - Submit → multipart POST /lab-reports with file + parsed JSON
 
- app/(tabs)/library.tsx — add a "Lab reports" section below tracked items, list cards with date, lab name, count of flagged values. Tap → /lab/[id].
  - (Alternative: lab reports get their own tab. Decide based on whether the Insights tab feels too empty in Phase 1 — for now, keep them in Library.)
 
- app/lab/[id].tsx
  - Header: lab_name + report_date in displayM
  - "View original" button (opens file via signed URL using expo-web-browser or in-app PDF viewer for PDFs)
  - Tests table:
    - Geist Mono for values and reference ranges (tabular alignment)
    - Flag column shows colored typographic badge: --positive "Normal", --warning "Low" / "High", --critical "Critical"
    - Long press a test row → option to "Convert to tracked measurement" (creates a measurements row with the same value, useful for HbA1c, fasting glucose, etc.)
  - Edit / Delete buttons in header
 
Required state handling:
- File upload progress bar during multipart submit
- Retry on network failure
- Validation: at least one test row required
 
After completion: upload a sample PDF lab report with 6 tests (2 flagged), view it, convert HbA1c to a measurement, verify it appears in /measurement/hba1c.
```
 
---

### Prompt 13 — Insights, history, onboarding, settings, polish

```
Final Phase 1 prompt. Ship the remaining surfaces and polish the rough edges.
 
Insights tab (app/(tabs)/insights.tsx):
- Header "Insights" in displayM
- Three section cards:
  1. Adherence — last 30 days. Bar showing % medications taken, % water target days hit, % workouts completed. Each row uses Sparkline-style minimal bars, no colour beyond --ink and --hairline.
  2. Trends — list of measurement types with their 30-day direction (▲ ▼ —) and current value. Tap → /measurement/[type].
  3. Lab summary — count of reports added, count of flagged tests in last 90 days.
- Empty state until at least 7 days of data exist
 
History (accessible from settings or as a section in Insights):
- /history screen
- Filter chips: All, Medications, Water, Workouts, Meals, Custom
- Date range picker
- Vertical list of log_entries, newest first, infinite scroll
- Each row: time (Geist Mono --slate), tracked item name, action ("Taken" --positive, "Skipped" --warning, etc.)
 
Settings tab (app/(tabs)/settings.tsx):
- Account section — Phase 1 just shows "Guest mode" with explanation, "Sign in to back up" stub
- Notifications — toggle, deep link to OS settings
- Timezone — read-only display
- Data — Export all data (JSON), Delete all data (with confirm)
- About — version, build, link to privacy policy URL (use a placeholder URL for now)
 
Onboarding (first-run, gated by AsyncStorage flag):
- Three screens, swipeable:
  1. Title "Your wellness, in one place." Subtitle. Continue button.
  2. Title "Reminders that respect your day." Body about how Phase 1 keeps it manual and private. Continue.
  3. Title "Add what matters first." Continue.
- On the third screen's Continue: request notification permission, then route to Library/new to create the first tracked item.
 
Edge case polish:
- Network error component: --slate banner at top of screen with retry, never blocks UI
- Loading skeletons for all list screens (not spinners — use hairline placeholder bars)
- Pull-to-refresh on Today, Library, Insights
- Accessibility pass: every Pressable has accessibilityLabel, every icon used semantically has accessibilityRole, font scales respect OS settings up to 1.3x without breaking layouts
- Haptics: light haptic on log action confirm, success haptic on submit, error haptic on validation failure
 
After completion: do a full end-to-end run — fresh install, onboarding, create a medication, receive a notification, tap Taken, view it on Today, view it in History, view adherence on Insights, export data, verify the JSON contains everything.
```


---

## 7. Design generation prompt (for Canva, Figma First Draft, etc.)
Use this prompt to generate a high-fidelity visual mockup of the Today dashboard before queuing Prompt 7 (the mobile build prompt) in Claude Code.

## Which tool to use

Paste this prompt into **one of these**, in order of preference:

1. **v0.dev** — best for high-fidelity mobile app UI from text prompts. Outputs React + Tailwind code you can ignore; keep the visual.
2. **Lovable.dev** or **bolt.new** — same idea, slightly different aesthetics.
3. **Claude.ai** (a fresh chat) — ask for an HTML/Tailwind mobile mockup; screenshot it.
4. **Galileo AI** or **Uizard** — if you prefer a design-tool UX over a code-output UX.
   Avoid Canva's AI and Figma First Draft for this — they're tuned for marketing graphics, not app UI with this much specification.

---

## The prompt (copy-paste, full)

```
Design a single mobile screen (390 × 844 px) for a premium health-tracking app called Vital. Aesthetic direction is editorial clinical — like a refined medical journal with considered colour. Monocle magazine layout discipline + New England Journal of Medicine's restraint + Aesop's earthy palette + Apple Health's data clarity. Premium, calm, signal-rich, never decorative.
 
═══════════════════════════════════════════════
STRICT RULES — DO NOT VIOLATE
═══════════════════════════════════════════════
- No purple-to-pink gradients. No multi-stop gradients of any kind.
- No glassmorphism, no frosted blurs, no glow effects.
- No neon, no electric blue, no cyan, no fluorescent anything.
- No emoji anywhere in the UI.
- No 3D / claymorphic icons. Outline icons only, 1.5px stroke.
- No pill-shaped buttons. No rounded blobs. Radius 8–10px max.
- No shadows except one barely-perceptible card shadow on Today cards.
- Colour must encode meaning. No decorative colour, no rainbow palettes.
 
═══════════════════════════════════════════════
COLOUR SYSTEM
═══════════════════════════════════════════════
 
SURFACES & TEXT (neutral foundation)
- Background:        #F7F4ED  (warm bone, slightly warmer than pure cream)
- Card surface:      #FFFFFF
- Elevated card:     #FFFFFF with 1px border #E8E3D8 (no shadow)
- Primary text:      #1A1A1A
- Secondary text:    #5C5C5C
- Tertiary / labels: #8C8C8C
- Hairline borders:  #E8E3D8
- Subtle divider:    #F0EBE0
 
CATEGORY ACCENTS (muted, journal-quality — never bright)
Each category gets its own restrained colour. Used on category icons,
the left edge of timeline items (2px tint), and category labels.
 
- Medication:  #4A5D7E  (slate navy — clinical, trustworthy)
- Hydration:   #5B8A8F  (muted seafoam teal — water but not "tech teal")
- Activity:    #8B5A3C  (warm clay brown — earthy, grounded)
- Nutrition:   #7A6F4D  (olive ochre — food, not appetite-bright)
- Vitals:      #6B4E71  (dusky plum — measurement, considered)
- Custom:      #6B6F4D  (sage — neutral fallback)
 
STATUS COLOURS (saturated enough to scan, muted enough to be premium)
- Taken / on-target:    #3F6B4E  (muted forest green)
- Pending / upcoming:   #B07A1F  (warm amber, used sparingly — only for items past their fire time)
- Missed / overdue:     #B85C3C  (muted terracotta, only for clear misses)
- Critical / flagged:   #8B2C1F  (deep brick, lab flags only)
- Neutral state:        #5C5C5C  (secondary text)
 
DATA VISUALIZATION
- Sparkline lines:           #1A1A1A   (primary text colour, 1.5px stroke)
- Sparkline fills:            none (line only)
- Trend up (good context):   #3F6B4E
- Trend down (good context): #3F6B4E   (e.g. weight loss is positive — context determines colour, not direction)
- Trend neutral / flat:      #8C8C8C
- Reference range bands:     #E8E3D8 at 40% opacity
 
═══════════════════════════════════════════════
TYPOGRAPHY
═══════════════════════════════════════════════
- Display headlines & large numbers:  Fraunces (variable serif, semibold ~580 weight, optical size aware, tight leading 1.1)
- Body & UI:                          Geist Sans (regular 400, medium 500, semibold 600)
- Numbers in charts, timestamps, log times:  Geist Mono (regular 400, medium 500)
- Section labels:                     Geist Sans, uppercase, 11px, letter-spacing 0.08em, #8C8C8C
- Body copy:                          15px / line-height 1.4
- Captions:                           12px / #5C5C5C
 
═══════════════════════════════════════════════
SCREEN CONTENT (top to bottom)
═══════════════════════════════════════════════
 
1. STATUS BAR
   Standard iOS status bar area. Background #F7F4ED.
 
2. HEADER (24px top padding, 20px horizontal)
   Row layout:
   - Left:   "Good morning, Niranjan" in Fraunces 28px, #1A1A1A, semibold,
             tight leading. Below: "Wednesday, 20 May" in Geist Mono 13px, #8C8C8C.
   - Right:  Settings icon (lucide Settings, outline, 1.5px, 22×22, #5C5C5C).
 
3. SECTION LABEL "TODAY"
   Geist Sans uppercase 11px, letter-spaced, #8C8C8C, 32px top margin.
 
4. TIMELINE (vertical list of 5 items, 14px gap between items, 20px horizontal padding)
 
   Each timeline item is a row:
   - Left edge:  A 2px-wide vertical tint bar in the category accent colour,
                 8px tall, centred vertically. Sits 0px from card left edge.
   - Card:       White #FFFFFF, 1px border #E8E3D8, 8px corner radius,
                 padding 14px vertical, 16px horizontal.
   - Time:       Geist Mono 13px, #5C5C5C, 56px fixed-width column on left
   - Category icon: 18×18 outline lucide icon in the category accent colour
                    (e.g. Pill for medication, Droplet for water, Dumbbell for workout, Utensils for meal)
   - Title:      Geist Sans 15px medium, #1A1A1A
   - Subtitle:   Geist Sans 13px regular, #8C8C8C
   - Right side: Status indicator (see below)
 
   The 5 items:
 
   ┌─ 08:00 │ [Pill icon #4A5D7E]  Metformin 500mg
   │        │ with breakfast                              ✓ #3F6B4E
   │        │ STATE: taken — title strikethrough in #8C8C8C, time also #8C8C8C
   │
   ├─ 09:30 │ [Droplet icon #5B8A8F]  Hydration
   │        │ 250 ml                                       ✓ #3F6B4E
   │        │ STATE: taken — title strikethrough in #8C8C8C
   │
   ├─ 12:00 │ [Utensils icon #7A6F4D]  Lunch
   │        │ Light meal                                   ○ #8C8C8C
   │        │ STATE: pending (future) — full opacity, neutral indicator
   │
   ├─ 17:30 │ [Dumbbell icon #8B5A3C]  Strength workout
   │        │ 45 min · Gym                                 ○ #8C8C8C
   │        │ STATE: pending (future) — full opacity, neutral indicator
   │
   └─ 20:00 │ [Pill icon #4A5D7E]  Metformin 500mg
            │ with dinner                                  ○ #8C8C8C
            │ STATE: pending (future) — full opacity, neutral indicator
 
   Status indicator on right of each row:
   - Taken:    Small filled check ✓ in #3F6B4E, 16×16
   - Pending:  Small outline circle ○ in #8C8C8C, 14×14
   - Missed:   Small outline circle with slash ⊘ in #B85C3C, 14×14
   These are typographic / iconic — no coloured backgrounds, no chips, no pills.
 
5. SECTION LABEL "RECENT" (32px top margin, 16px bottom margin)
 
6. MEASUREMENT CARDS (horizontal scroll, 3 cards visible)
   Each card:
   - White surface #FFFFFF, 1px border #E8E3D8, 12px corner radius
   - 160×140px, 12px gap between cards
   - Padding 16px
 
   Card 1 — WEIGHT
   - Label "WEIGHT" — Geist Sans uppercase 11px, letter-spaced, #6B4E71 (vitals accent)
   - Value "72.4" in Fraunces 36px semibold #1A1A1A, with "kg" beside it in Geist Sans 14px #8C8C8C
   - Delta row: "▼ 0.8 kg" in Geist Mono 12px #3F6B4E, then "vs 30d avg" in 12px #8C8C8C
   - Sparkline: 14-day line, #1A1A1A, 1.5px stroke, no fill, no axes, 30px tall
 
   Card 2 — BLOOD PRESSURE
   - Label "BLOOD PRESSURE" — same style, accent #6B4E71
   - Value "118/76" in Fraunces 36px #1A1A1A, "mmHg" beside in 14px #8C8C8C
   - Status pill: "WITHIN RANGE" in Geist Sans uppercase 10px, letter-spaced,
                  background #F0EBE0, text #3F6B4E, 4px radius, 6px horizontal padding
   - Sparkline: dual-line (systolic darker, diastolic lighter #8C8C8C)
 
   Card 3 — HBA1C
   - Label "HBA1C" — accent #6B4E71
   - Value "5.6" in Fraunces 36px #1A1A1A, "%" beside in 14px #8C8C8C
   - Caption "Last 4 months" in Geist Mono 12px #8C8C8C
   - Sparkline: 6-point line over months, #1A1A1A
 
7. SECTION LABEL "THIS WEEK" (32px top margin)
 
8. WEEKLY STATUS BLOCK
   White card #FFFFFF, 1px border #E8E3D8, 12px corner radius, 18px padding.
   Three stacked lines, 12px vertical gap:
 
   - "5 of 7 days on water goal."
     ↳ "5 of 7 days" in Geist Sans medium #1A1A1A,
       rest in regular #5C5C5C.
     ↳ Tiny status dot at row start: #3F6B4E, 6×6 circle.
 
   - "BP stable across 4 readings."
     ↳ "Stable" emphasized in medium #1A1A1A.
     ↳ Status dot: #3F6B4E.
 
   - "No missed medications."
     ↳ "No missed" emphasized in medium #1A1A1A.
     ↳ Status dot: #3F6B4E.
 
9. BOTTOM TAB BAR (fixed, 56px height, 1px top border #E8E3D8)
   Background #F7F4ED. Four equal-width tabs.
 
   - Today      — Home icon (outline, 1.5px, 22×22), label "Today" in 10px Geist Sans medium #1A1A1A
                  Active state: icon and label in #1A1A1A. A 2px wide × 18px tall vertical bar in #4A5D7E sits to the left of the icon (subtle active indicator, NOT a pill background).
   - Library    — Layers icon, label "Library" — inactive #8C8C8C
   - Insights   — Activity icon, label "Insights" — inactive #8C8C8C
   - Settings   — Settings icon, label "Settings" — inactive #8C8C8C
 
═══════════════════════════════════════════════
SPACING & LAYOUT
═══════════════════════════════════════════════
- Horizontal padding: 20px on all main content
- Section gap (label to first item): 16px
- Section gap (between major sections): 32px
- Timeline item vertical gap: 14px
- Tab bar height: 56px
- Safe area bottom: respected (don't let content sit under tab bar)
 
═══════════════════════════════════════════════
MOOD CHECK
═══════════════════════════════════════════════
The screen should feel like:
- A page from a well-designed health journal, not a fitness app
- Calm enough to look at first thing in the morning without effort
- Trustworthy enough that a 50-year-old managing hypertension would believe the numbers
- Restrained enough that nothing screams for attention — but rich enough that the eye finds rhythm and meaning in the small touches of category colour, the slate medication accents, the seafoam hydration tints, the warm clay activity marks
 
NOT:
- A wellness app screenshot meant for Instagram
- A "trendy fintech" colour palette pretending to be healthcare
- A monochrome graveyard with no signal at all
 
References to draw from:
- Apple Health's information hierarchy (but warmer)
- Things 3's typographic confidence
- One Medical's restraint
- Monocle magazine's category-tinted layouts
- New York Times Magazine's editorial elegance
- Aesop's earthy product packaging
- The New England Journal of Medicine's digital reading experience
```
 
---

## After you have a mockup you like

1. Screenshot the result (PNG, full mobile frame).
2. Save it to your workspace: `~/Code/vital/design-refs/today-screen.png`
3. When you queue Prompt 7 in Claude Code, attach this image to the prompt — Claude Code reads images. Add a one-line preface:
   > Reference image for the Today screen design is attached. The tokens and structure below match what's shown in the image. Where the image and prompt disagree, the prompt's hex codes and structural rules win.
4. The image acts as a *visual contract*. Claude Code matches it within the constraints of the design tokens already in `src/theme/tokens.ts`.
---

## Updating the design tokens

If you go with the richer category accents above, update `src/theme/tokens.ts` (after Prompt 6 finishes) to include them:

// Category accents
'categoryMedication': '#4A5D7E',
'categoryHydration':  '#5B8A8F',
'categoryActivity':   '#8B5A3C',
'categoryNutrition':  '#7A6F4D',
'categoryVitals':     '#6B4E71',
'categoryCustom':     '#6B6F4D',

// Updated status
'missed':   '#B85C3C',   // muted terracotta
'divider':  '#F0EBE0',

// Updated background — slightly warmer
'bone':     '#F7F4ED',
'hairline': '#E8E3D8',

The original v2 spec uses a single teal accent. If you adopt the category-tinted version, do a search-replace in the v2 spec to update the tokens section. Or just paste the updates above into Prompt 6 when you run it: "use these tokens in src/theme/tokens.ts in addition to the ones in the spec."
---

## 8. Order of execution

Don't parallelize. Each prompt depends on the previous. Run backend prompts in `kyros-backend/`, then mobile prompts in `vital-mobile/`.

| # | Prompt | Repo | Estimated Claude Code time |
|---|---|---|---|
| 0 | Backend repo scaffold | kyros-backend | 20–30 min |
| 1 | SQLAlchemy models + Alembic | kyros-backend | 45–60 min |
| 2 | Pydantic schemas + core utils | kyros-backend | 60–90 min |
| 3 | API foundations + OpenAPI export | kyros-backend | 45–60 min |
| 4 | Tracked items + reminders + upcoming | kyros-backend | 90–120 min |
| 5 | Logs + measurements + lab reports | kyros-backend | 90–120 min |
| 6 | Mobile scaffold + typegen + design system | vital-mobile | 90–120 min |
| 7 | Today dashboard | vital-mobile | 90–120 min |
| 8 | Library + tracked item CRUD UI | vital-mobile | 120–180 min |
| 9 | Reminder builder + schedule UI | vital-mobile | 60–90 min |
| 10 | Local notification engine | vital-mobile | 90–120 min |
| 11 | Measurements + charts | vital-mobile | 90–120 min |
| 12 | Lab reports | vital-mobile | 90–120 min |
| 13 | Insights + history + onboarding + polish | vital-mobile | 120–180 min |

Total Claude Code time: **~18–24 hours** of focused execution. Realistic calendar to first beta user: **4–6 weeks**, including your review time, deployment setup, App Store / Play Store submission, and a small group of testers.

---

## 9. Lead-time items to start *this week*

These are the longest poles in the tent and don't depend on code:

1. **Domain registration + SSL** — pick the wellness app brand name and lock the domain today.
2. **EC2 instance + Postgres backup S3 bucket** — provision the t3.small in ap-south-1 now. Even if it sits idle for 2 weeks, it's ₹50.
3. **Apple Developer account (₹8,500/year)** — start the enrolment, it can take 2–7 days.
4. **Google Play Console account (one-time ₹2,000)** — start the enrolment.
5. **AiSensy application** — even though WhatsApp is Phase 2, the WABA approval takes 2–4 weeks. Apply now so it's ready when needed.
6. **Razorpay KYC** — Phase 2 dependency but KYC takes 3–4 weeks. Start month 3 of the build.

---

## 10. What Phase 2 adds (no Phase 1 rewrites)

When Phase 2 activates around month 5, you add:

1. `app/clinic/` populated: consultation, prescription, lab_order, doctor models and routes.
2. `app/integrations/kyros_intake.py` — a Kyros patient registration handshake: on first login, link `users.kyros_patient_id`.
3. `app/wellness/services/clinical_sync.py` — when a doctor adds a prescription in `clinic/`, mirror it as a `wn_tracked_item` with `source='kyros'` and `source_ref=<prescription_id>`.
4. **Mobile UI**: badge on Kyros-sourced rows ("From your Kyros chart"), lock direct edits with a hint to message the care coordinator.
5. **Subscription gating**: free vs plus vs kyros tier — paywall logic on advanced features.
6. **WhatsApp channel** in `reminders.channels` activated: dispatcher (Celery task) sends WhatsApp messages via AiSensy when `'whatsapp'` is in the array.

No schema migrations. No reminder engine rewrite. No dashboard redesign.

---

## 11. What Phase 3 adds (no Phase 1 rewrites)

Three independent capabilities:

1. **Multimodal capture endpoint** — `POST /v1/wellness/capture` accepts image / audio / text. Routes to:
   - Gemini 2.5 Pro for lab report OCR → structured `ParsedTest[]`
   - Gemini for prescription extraction → `MedicationMeta + Schedule`
   - Claude Sonnet 4.6 for medication-interaction safety summaries
   - Whisper or Gemini Audio for voice command parsing → intent + slots
   Returns a draft payload the user confirms before commit. Confirmed records get `source='ai_extracted'`.

2. **Voice command interface** in the mobile app — push-to-talk button, sends audio to `/capture`, applies the result on confirmation.

3. **Per-channel dispatcher upgrades** — when the user opts into WhatsApp or voice reminders, the dispatcher reads `channels` on the reminder and routes accordingly. Voice via Exotel TTS + outbound call API.

Data model is already ready. Reminder schema is already ready. Dashboard already reads from the same tables.

---
# Prompt: Phase 1 Admin Panel

**Repo:** `kyros-backend`
**Depends on:** Prompts 0–5 (scaffold, models, schemas, API foundations, items, logs) must be complete.
**Estimated time:** 90–120 min of Claude Code execution.
**Reviewer time:** ~30 min — this prompt touches auth, so eyeball every middleware change.

---

## Context

You are extending the existing FastAPI backend (`kyros-backend`) with a server-rendered HTML admin panel mounted at `/admin`. This is **Phase 1 admin** — single-user (the founder), behind HTTP Basic Auth, intentionally boring. Do not build a SPA. Do not add a frontend build step. Do not introduce a new framework. Jinja2 templates only.

The admin panel coexists with the JSON API. The same FastAPI app serves both. The JSON API stays untouched.

### Locked decisions for this prompt

1. **Mount point:** all admin routes live under `/admin/*`. The root admin URL is `/admin/`.
2. **Auth:** HTTP Basic Auth via FastAPI's `HTTPBasic` security. Credentials come from env vars `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` (bcrypt hash, not plaintext). Failed auth returns 401 with `WWW-Authenticate: Basic`.
3. **Rendering:** Jinja2 templates in `app/admin/templates/`. Static assets (one CSS file, no JS bundler) in `app/admin/static/`.
4. **Read-mostly:** the only write actions in this prompt are (a) marking a consultation status, (b) discontinuing a tracked item, (c) toggling a reminder active flag. Everything else is read-only.
5. **Confirmation pattern:** every write action renders a confirmation page where the admin must type a specific phrase (e.g. "DISCONTINUE") before the POST is accepted. Server validates the phrase. No JS-based confirmations.
6. **Audit:** every admin action (including GETs on sensitive resources like individual user detail and consultation detail) writes an `audit_log` row with `actor_type='admin'`, `action='admin.<verb>.<resource>'`, and the full request path in `payload`.
7. **No PHI in admin logs.** When writing application logs (structlog), redact `payload`, `metadata`, and any field named `notes`, `dose`, `lab_value`, or `result`. The admin UI itself can show these — but structlog must not.
8. **Read replica not used.** Phase 1 has one Postgres. Admin queries hit the same DB but use `SELECT` with `statement_timeout = 5000ms` set at the session level to prevent a runaway admin query from killing the app.

### What this prompt does NOT do

- No role hierarchy. Add a `users.role` column (default `'user'`) for future use, but only `'superadmin'` is recognized. Don't build a permission system yet.
- No CSV export. Add it in Phase 1.5.
- No user impersonation. Add it in Phase 1.5.
- No SQL console. Never.
- No charts/graphs. Numbers in tables. If you want a chart later, add it then.
- No password reset flow. If the admin loses access, they SSH into the EC2 box and re-set the env var.

---

## Required changes

### 1. Add `kc_consultations` table (new)

Marketing site booking flow lands here. Add to Alembic migrations.

```sql
CREATE TABLE kc_consultations (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
  patient_name      TEXT NOT NULL,
  patient_phone     TEXT NOT NULL,
  patient_email     TEXT,
  condition_category TEXT,
  preferred_slot    TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'requested',
                    -- 'requested' | 'scheduled' | 'completed' | 'cancelled' | 'no_show'
  meeting_link      TEXT,
  meeting_provider  TEXT,   -- 'zoom' | 'meet' | null
  scheduled_at      TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  fee_paid_paise    INTEGER,
  razorpay_payment_id TEXT,
  source            TEXT NOT NULL DEFAULT 'web',  -- 'web' | 'admin' | 'whatsapp'
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_kc_consult_status ON kc_consultations(status, preferred_slot);
CREATE INDEX idx_kc_consult_user ON kc_consultations(user_id);
CREATE INDEX idx_kc_consult_phone ON kc_consultations(patient_phone);
```

Add corresponding SQLAlchemy model `app/clinic/models/consultation.py` (create the `app/clinic/models/` package if it doesn't exist). Follow the same `Mapped[]` style as existing wellness models.

### 2. Add `users.role` column

Alembic migration: `ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user';`

Update the `User` SQLAlchemy model. Add a check constraint or simple validation that `role IN ('user', 'superadmin')` for now — keep room for future roles by not making it an enum type at the DB level.

### 3. Admin app structure

```
app/admin/
├── __init__.py
├── auth.py              # HTTPBasic dependency, bcrypt verify
├── deps.py              # require_admin() dependency, get_admin_db()
├── routes/
│   ├── __init__.py
│   ├── dashboard.py     # GET /admin/
│   ├── users.py         # GET /admin/users, GET /admin/users/{id}
│   ├── items.py         # GET /admin/items, POST /admin/items/{id}/discontinue
│   ├── reminders.py     # GET /admin/reminders, POST /admin/reminders/{id}/toggle
│   ├── consultations.py # GET /admin/consultations, POST /admin/consultations/{id}/status
│   ├── audit.py         # GET /admin/audit
│   └── health.py        # GET /admin/health (system status)
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── users_list.html
│   ├── user_detail.html
│   ├── items_list.html
│   ├── reminders_list.html
│   ├── consultations_list.html
│   ├── consultation_detail.html
│   ├── audit_log.html
│   ├── health.html
│   └── confirm_action.html  # reusable confirmation page
├── static/
│   └── admin.css        # ~150 lines, no framework
└── services/
    ├── metrics.py       # all dashboard queries in one place
    └── audit.py         # write_admin_audit(action, resource_type, resource_id, payload)
```

Register the admin router in `app/main.py` AFTER the JSON API routers, mounted at `/admin`. Mount the static dir at `/admin/static`.

### 4. The dashboard (`GET /admin/`)

Render `dashboard.html` with these metrics. Compute all of them in `services/metrics.py` as separate functions so they can be unit-tested. Cache the result for 30 seconds in-process (a simple dict with a timestamp — don't reach for Redis for this).

**Block 1: Users**
- Total users
- Active in last 7 days (any `audit_log` entry where `actor_type='user'`)
- Active in last 30 days
- New users in last 7 days
- Users with email set (i.e. moved past guest mode)

**Block 2: Tracked items**
- Total by status: active / paused / discontinued
- Total by category (medication, hydration, activity, nutrition, vitals, custom)
- Items created in last 7 days
- Items discontinued in last 7 days

**Block 3: Reminders & adherence**
- Total reminders, active reminders
- Fires expected per day (sum from `expand_schedule` over next 24h)
- Last 7 days adherence: `taken / (taken + skipped + missed)` across all log entries
- Last 7 days missed count (reminders that fired with no log entry within 4 hours)

**Block 4: Consultations**
- Bookings in last 7 days
- Status breakdown: requested / scheduled / completed / cancelled / no_show
- Upcoming in next 48 hours (count)
- Revenue last 30 days (sum of `fee_paid_paise` where status = 'completed')

**Block 5: System**
- DB connection: ok/fail (simple `SELECT 1` with timeout)
- Redis connection: ok/fail
- Last successful Alembic migration timestamp (read from `alembic_version`)
- Disk usage on /var/lib/docker (call `shutil.disk_usage`)
- Sentry link (just a static `<a>` to your Sentry project URL from env var `SENTRY_DASHBOARD_URL`)
- Better Stack link (similar, from `UPTIME_DASHBOARD_URL`)

**Block 6: Recent activity**
- Last 20 rows from `audit_log`, newest first, with a "view full log" link to `/admin/audit`.

### 5. List views

Each list view supports:
- Pagination via `?page=N&size=50` query params (server-side, simple LIMIT/OFFSET)
- A free-text search box (only on users — searches phone / email / device_id with `ILIKE %query%`)
- A status filter dropdown where applicable
- Server-side sort by `created_at DESC` default

`GET /admin/users` — columns: id (truncated), phone-or-device-id, email, tier, role, created_at, item_count, last_activity_at. Each row links to `/admin/users/{id}`.

`GET /admin/users/{id}` — user detail page showing:
- Identity block (id, device_id, email, phone, timezone, tier, role, created_at)
- Tracked items table (all of them — link to items list filtered by this user)
- Recent log entries (last 30)
- Recent audit log entries for this user (last 30)
- Linked Kyros consultations (if any)
- **No edit buttons in this prompt.** View-only.

`GET /admin/items` — columns: id, user (link), category, name, status, start_date, source, reminders_count. Filter by status, category, source. Action button per row: "Discontinue" (if status='active') → goes to confirmation page → POST `/admin/items/{id}/discontinue`.

`GET /admin/reminders` — columns: id, item (link), schedule summary, channels, active. Toggle action per row: "Pause" / "Resume" → confirmation → POST `/admin/reminders/{id}/toggle`.

`GET /admin/consultations` — columns: id, patient_name, patient_phone, condition_category, status, preferred_slot, fee_paid_paise. Filter by status. Each row links to `/admin/consultations/{id}`.

`GET /admin/consultations/{id}` — full consultation detail. Form to update:
- `status` dropdown (requested → scheduled → completed/cancelled/no_show)
- `meeting_link` (text input)
- `meeting_provider` (zoom/meet)
- `scheduled_at` (datetime-local input)
- `notes` (textarea)

Submitting POSTs to `/admin/consultations/{id}/status` which renders confirmation page first.

`GET /admin/audit` — paginated `audit_log` viewer. Filter by `actor_type`, `action`, `user_id`, date range. Newest first. JSON `payload` shown as `<pre>` formatted.

### 6. Confirmation page pattern

`templates/confirm_action.html` takes:
- `action_label` — e.g. "Discontinue tracked item: Atorvastatin 10mg"
- `action_description` — what will happen, in plain English
- `confirmation_phrase` — the exact text the admin must type (e.g. `DISCONTINUE`)
- `submit_url` — where the form posts
- `cancel_url` — where the cancel button goes

The route handler validates `request.form['confirmation']` equals `confirmation_phrase` (case-sensitive). If wrong, re-render with an error. If correct, perform the action, write audit log, redirect to the list view with a flash message.

Use FastAPI's `Request` object for form parsing. No CSRF library needed for Phase 1 — Basic Auth with browser-stored credentials and the typed-phrase requirement are sufficient. (Add CSRF tokens in Phase 1.5 alongside the move to session-based auth.)

### 7. The audit helper

`services/audit.py` exposes one function:

```python
async def write_admin_audit(
    db: AsyncSession,
    request: Request,
    action: str,
    resource_type: str | None = None,
    resource_id: UUID | None = None,
    payload: dict | None = None,
) -> None
```

Call this from every admin route — both reads (for sensitive views like user detail and consultation detail) and writes. The `request` is used to extract IP and user-agent. The acting admin's username goes into `payload['admin_username']`.

Dashboard, list views, and the audit log viewer itself are NOT audited (would create infinite noise). Detail views and all writes ARE audited.

### 8. Styling

One CSS file. ~150 lines. Match the Kyros aesthetic from `kyros-design-decisions` skill if you can read it — restrained, serif headings (Fraunces if available via Google Fonts CDN, else Georgia), sans body (Inter via CDN, else system-ui). Otherwise just clean and boring:

- Bone background (`#F7F4ED`), text `#1A1A1A`
- Tables: hairline borders `#E8E3D8`, no zebra striping, generous padding
- Buttons: bordered, no shadows. Destructive actions get a `#B85C3C` border.
- Forms: stacked labels, full-width inputs
- Top nav: simple horizontal bar with links to each section, current section underlined
- No icons. No JavaScript. Forms submit and reload.

The point is that admin should look like a 2010 internal tool. It's faster to read, faster to build, and signals the right "be careful, this is real data" tone.

### 9. Environment variables to add

Update `.env.example` and the settings module (`app/core/config.py`):

```
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<bcrypt hash, generate with passlib>
SENTRY_DASHBOARD_URL=https://sentry.io/organizations/your-org/projects/kyros-backend/
UPTIME_DASHBOARD_URL=https://uptime.betterstack.com/...
ADMIN_SESSION_TIMEOUT_MINUTES=60   # informational only in Phase 1
```

Add a one-off CLI command `poetry run python -m app.admin.cli set-password` that prompts for a password and prints the bcrypt hash to stdout. The admin then puts that hash in `.env`. Do not write plaintext passwords to disk or logs.

### 10. Tests

In `tests/admin/`:
- `test_auth.py` — 401 without creds, 401 with wrong creds, 200 with right creds, no caching of failed attempts in memory
- `test_dashboard.py` — every metric function returns the right shape, dashboard renders 200 with all blocks
- `test_confirmation.py` — wrong phrase rejects, right phrase commits, audit row written
- `test_audit_redaction.py` — verify structlog output does NOT contain a known PHI field after an admin views a consultation that has notes

Don't aim for 100% coverage. Cover auth, the confirmation pattern, and the redaction guarantee. Those are the load-bearing pieces.

### 11. Documentation

Add `docs/ADMIN.md`:
- How to set the admin password (the CLI command)
- The URL: `https://api.kyros.clinic/admin/` once Caddy is configured
- The list of write actions and what they do
- The audit log retention policy (forever, in Phase 1 — no purge job)
- How to add a second admin in Phase 1.5 (preview: switch to `users.role='superadmin'` lookup instead of env-var auth)

---

## Acceptance criteria

Before declaring this prompt done:

1. `curl https://localhost/admin/` returns 401 with `WWW-Authenticate: Basic`.
2. With valid Basic Auth, the dashboard loads in under 500ms on a t3.small with 1000 seeded users.
3. Discontinuing an item via the admin UI sets `status='discontinued'` AND writes an `audit_log` row visible at `/admin/audit`.
4. Typing the wrong confirmation phrase shows an inline error and does NOT mutate any data.
5. `grep -r "X-Device-Id\|patient_phone\|notes\|dose" logs/` after an admin session shows zero PHI leaks.
6. The booking endpoint for `www.kyros.clinic` is NOT in this prompt — it's a separate concern. Admin can only manage consultations that already exist. Bookings come from a future prompt.
7. `mypy --strict app/admin/` passes.
8. `ruff check app/admin/` passes.

---

## Things to NOT do (anti-checklist)

- ❌ Don't add React, HTMX, Alpine, or any client-side framework.
- ❌ Don't add a SQL console or "raw query" endpoint.
- ❌ Don't add user impersonation. Deferred to Phase 1.5.
- ❌ Don't add CSV export. Deferred to Phase 1.5.
- ❌ Don't add charts. Numbers in tables only.
- ❌ Don't add role management UI. The role column is for future use.
- ❌ Don't add password change UI. CLI only in Phase 1.
- ❌ Don't add session-based auth. HTTP Basic is sufficient for one admin.
- ❌ Don't add a "delete user" action. Soft-delete only, and not from admin in Phase 1.
- ❌ Don't add prescription writing. That's Phase 2.
- ❌ Don't add the booking form endpoint. Separate prompt.

If any of these feel necessary while implementing, stop and ask before doing them. The constraint is the point.

---

## Deliverable

A working `/admin/` mount on the FastAPI backend, behind HTTP Basic Auth, that lets a single founder-admin see what's happening in the database, manage consultations, and discontinue items — without ever giving them a sharp enough tool to hurt themselves with at 2am.
*End of build spec v2.*
