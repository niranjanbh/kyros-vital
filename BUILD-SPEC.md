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

### Prompts 7–13 — Mobile feature screens

These are **unchanged from v1** in structure. The only difference: wherever v1 referenced `packages/types`, v7+ reference `src/api/generated/schema.ts` types instead, accessed via `openapi-fetch` typed responses.

For brevity, here are the prompt titles. The full text from v1 of the spec applies, with the following find-replace:
- `packages/types` → `src/api/generated`
- `Zod schemas from packages/types` → `types from src/api/generated/schema.ts + Zod schemas defined inline in src/api/schemas/`
- `TanStack Query hook for /reminders/upcoming` → `TanStack Query hook for /v1/wellness/reminders/upcoming` (note the `/v1/wellness/` prefix throughout)

The full prompts:
- **P7** — Today dashboard (timeline, sparkline cards, weekly status)
- **P8** — Library + tracked item CRUD UI (category-grouped list, per-category forms, detail view)
- **P9** — Reminder builder + schedule UI primitives (ScheduleBuilder, RecurringBuilder, IntervalBuilder)
- **P10** — Local notification engine (expo-notifications, scheduler.sync(), action handlers, snooze)
- **P11** — Measurements + charts (entry forms, Victory Native trend charts, BP dual-line)
- **P12** — Lab reports (camera/file upload, manual data entry, list + detail)
- **P13** — Insights, history, onboarding, settings, polish

Run them in order. Each one ships a vertical slice that compiles and runs.

---

## 7. Design generation prompt (for Canva, Figma First Draft, etc.)

Unchanged from v1. Paste this into your design tool of choice:

```
Design a single mobile screen (390 × 844 px) for a premium health-tracking app called Vital. Aesthetic direction is editorial clinical — like a refined medical journal, not a consumer wellness app.

STRICT RULES — DO NOT VIOLATE:
- No purple-to-pink gradients. No glassmorphism. No neon. No 3D icons.
- No bright blues or cyans. No "tech" accent colors.
- No emoji anywhere in the UI.
- No rounded blobs or pill-shaped buttons.

Colour palette (use these exact values):
- Background: #FAF8F4 (warm bone white)
- Card surface: #FFFFFF
- Primary text: #1A1A1A
- Secondary text: #595959
- Tertiary text / labels: #8C8C8C
- Hairline borders: #E8E5DD (use 1px borders, NOT shadows)
- Accent: #2D5F5D (deep teal) — use sparingly, only for one primary CTA or active states
- Positive state: #3F6B4E
- Warning state: #B07A1F
- Critical: #8B2C1F

Typography:
- Display headlines and large numerical values: Fraunces (serif, semibold, tight leading)
- Body and UI text: Geist Sans (regular and medium)
- Numbers in charts and timestamps: Geist Mono
- Labels: Geist Sans, uppercase, letter-spaced, 11px, tertiary text color

Screen content, top to bottom:
1. Status bar area at top.
2. Header row: "Good morning, Niranjan" in Fraunces 28px, with "Wednesday, 20 May" below in Geist Mono 13px tertiary text. Small outline settings icon top-right.
3. Section label "TODAY" (caption, uppercase).
4. Timeline of 5 reminders for today:
   - 08:00 — Metformin 500mg, subtitle "with breakfast", state: ✓ taken (strikethrough, secondary text)
   - 09:30 — Glass of water, subtitle "250 ml", state: ✓ taken
   - 12:00 — Lunch, subtitle "Light meal", state: pending
   - 17:30 — Strength workout, subtitle "45 min · Gym", state: pending
   - 20:00 — Metformin 500mg, subtitle "with dinner", state: pending
   Each row: time on left in mono, title and subtitle in middle, status indicator on right (small typographic check or — symbol).
5. Section label "RECENT".
6. Horizontal scroll of 3 measurement cards, each white with hairline border:
   - "WEIGHT" label, "72.4 kg" in Fraunces 36px, "▼ 0.8 kg vs 30d avg" in mono caption positive color, small sparkline below
   - "BLOOD PRESSURE" label, "118/76" in Fraunces 36px, "Within range" in caption positive, sparkline below
   - "HBA1C" label, "5.6 %" in Fraunces 36px, "Last 4 months" in caption secondary, sparkline below
7. Section label "THIS WEEK".
8. Three plain-text status lines: "5 of 7 days on water goal." / "BP stable across 4 readings." / "No missed medications."
9. Bottom tab bar: 4 tabs (Today, Library, Insights, Settings), single-line icons (no fills), Today active in primary text, others in tertiary. Hairline top border.

Spacing: generous, 24px between sections, 12px between timeline items.
Mood: calm, premium, restrained. The kind of screen a 45-year-old would trust with their lab results, not the kind a 22-year-old would screenshot for Instagram.

Reference inspirations: Apple Health's restraint, Things 3's typography, One Medical's app, the New York Times Magazine's editorial layout — combined.
```

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

*End of build spec v2.*
