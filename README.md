# MSCS-699-HealthTrackerApp

FastAPI backend for the HealthTrack API. Project Phase 3 replaces the Phase 2
in-memory skeleton with a real PostgreSQL-backed data layer (SQLAlchemy +
Alembic), JWT authentication, and role-based access control for patients,
vital signs, and activity data. Alert thresholds/alerts/risk scores are still
the Phase 2 in-memory stubs -- those become real in Phase 4/5.

For the original Phase 2 skeleton (in-memory only, no auth, no database, runs
with zero setup), see [README-Phase2.md](README-Phase2.md).

## Setup

You need a running PostgreSQL server reachable from this machine (tested
against Postgres 18, but any recent version works).

```bash
git clone https://github.com/olkanth/MSCS-699-HealthTrackerApp.git
cd MSCS-699-HealthTrackerApp

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DATABASE_URL (percent-encode any special characters in the
# password, e.g. "@" -> "%40"), and set SECRET_KEY to a random string
# (python -c "import secrets; print(secrets.token_hex(32))")

alembic upgrade head                # builds all 9 tables from the migrations

fastapi dev
```

Then open **http://localhost:8000/docs** for Swagger UI.

**Database creation is automatic:** the app creates the database itself
(if it doesn't exist yet) on startup, via a FastAPI lifespan handler --
you don't need to run anything extra before `alembic upgrade head`. This
is a convenience for local dev/grading only, not something a production
deployment should rely on (see the comment on `lifespan()` in
`app/main.py` for why); `python scripts/create_database.py` still exists
if you want to create the database without starting the full app.

**If you already loaded `DBSchema.sql` by hand** (e.g. following the Phase 2
setup), the tables already exist -- run `alembic stamp head` instead of
`alembic upgrade head`, so Alembic knows not to try creating them again.

**Note:** running `pip install` without the venv steps above fails on
Ubuntu 24.04 with `error: externally-managed-environment` -- create and
activate the venv first and it installs cleanly.

`API-Documentation.json` is a live snapshot of the same API docs, pulled from
a running instance, in case you just want the spec without running the code.

## Running the tests

```bash
pytest -v
```

Tests run against the same `DATABASE_URL` the app uses, but each test opens
its own transaction and rolls it back afterwards, so nothing a test writes
(or a call to `commit()` inside app code) ever persists, and the sample data
in your database is never touched.

## API workflow guide

1. `POST /auth/register` with `{username, email, password, role}` --
   `role` is one of `patient`, `provider`, `admin`, `it_staff`.
2. `POST /auth/login` (OAuth2 form fields: `username`, `password`) returns
   `{access_token, token_type}`.
3. Send `Authorization: Bearer <access_token>` on every other request.
4. **Patient self-service flow:** register/login as `patient` -> `POST
   /patients/` (no `user_id` needed, it's linked to your own account
   automatically) -> `POST /vital-signs/` / `POST /activity-data/` to record
   readings -> `GET /vital-signs/?patient_id=...` (optionally with
   `start`/`end` date filters) to review history.
5. **Provider/admin flow:** register/login as `provider` or `admin` -> `GET
   /patients/` to list everyone -> `POST /patients/` with an explicit
   `user_id` to onboard a patient's clinical profile on their behalf -> read
   or update any patient's records.

### Quick example: register a fresh account and create a patient

```bash
# 1. Register a new patient-role login account
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "newpatient1", "email": "newpatient1@example.com", "password": "password123", "role": "patient"}'

# 2. Log in as that account (OAuth2 form fields, not JSON)
curl -X POST http://localhost:8000/auth/login \
  -d "username=newpatient1&password=password123"
# -> {"access_token": "...", "token_type": "bearer"}

# 3. Create a patient profile with that token (no user_id needed -- it's
#    linked to your own account automatically)
curl -X POST http://localhost:8000/patients/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token from step 2>" \
  -d '{"first_name": "New", "last_name": "Patient", "date_of_birth": "1990-01-01", "mrn": "MRN-90001"}'
```

**Note:** each login account can be linked to at most one patient profile
(`patients.user_id` is `UNIQUE`). The seeded sample accounts (`jsmith`,
`mgarcia`) already have a profile from `DBSchema.sql`'s sample data, so
`POST /patients/` with one of those tokens returns `409` -- register a new
account like above instead, or reuse the existing profile via `GET`/`PUT
/patients/{id}`.

### Roles and access

- `patient` -- only their own patient profile, vital signs, and activity data.
- `provider` / `admin` -- any patient's records; only these two can list all
  patients or delete a patient profile.
- `it_staff` -- no clinical-data access at all (account/system administration
  only), per the minimum-necessary principle from the Phase 1 HIPAA notes.

### Error responses

- `401` -- missing, malformed, or expired bearer token.
- `403` -- valid token, but the wrong role or wrong patient ownership.
- `404` -- record not found.
- `409` -- duplicate value (e.g. MRN or username already in use).
- `422` -- validation error (bad `blood_pressure` format, out-of-range
  heart rate, missing required field).

Every request that succeeds against `/patients`, `/vital-signs`, or
`/activity-data` writes a row to `audit_log` (user, action, table, record id)
-- list endpoints are the one exception, to avoid flooding the log.

## Performance baseline

`python scripts/performance_check.py` times a handful of list/get endpoints
and runs `EXPLAIN ANALYZE` on a patient+date-range vital-signs query to
confirm the `idx_vitals_patient_time` index is used. This is a baseline
measurement for the Phase 3 report, not optimization work -- bottleneck
analysis and tuning are Phase 6 (Performance Optimization) scope.



# Phase 3 changes and review

### Files added or changed since Phase 2

This repo carries every phase's submission, so here's a manifest of exactly
what Phase 3 touched, for a reviewer who already looked at Phase 2 and just
wants to see the delta rather than re-reading the whole tree.

**New files:**

- `app/config.py` -- settings (`DATABASE_URL`, `SECRET_KEY`, etc.) loaded from `.env`.
- `app/database.py` -- SQLAlchemy engine/session setup, `get_db()`, `ensure_database_exists()`.
- `app/models.py` -- SQLAlchemy ORM models for all 9 `DBSchema.sql` tables.
- `app/services.py` -- the data access/service layer (CRUD, filtering, domain exceptions, logging).
- `app/auth.py` -- password hashing, JWT issuing/verification, RBAC dependencies.
- `app/routers/auth.py` -- `POST /auth/register`, `POST /auth/login`.
- `app/tests/` (new directory) -- `conftest.py` plus `test_models.py`, `test_auth.py`,
  `test_patients_api.py`, `test_vital_signs_api.py`, `test_activity_api.py`,
  `test_audit_log.py` (45 tests total).
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`,
  `alembic/versions/605af560fc9e_core_identity_tables.py`,
  `alembic/versions/32fadc579546_clinical_data_tables.py` -- migration setup and the two migrations.
- `scripts/create_database.py` -- standalone "create the database if missing" step.
- `scripts/performance_check.py` -- baseline timing + `EXPLAIN ANALYZE` script.
- `.env.example` -- template for the required environment variables (`.env` itself is
  gitignored and never committed).
- `HealthTrackerApp.postman_collection.json` -- Postman collection covering every endpoint.
- `README-Phase2.md` -- the original Phase 2 README, preserved as-is (see below).

**Modified files:**

- `app/main.py` -- registers the new `auth` router; added the `lifespan` handler that
  creates the database on startup.
- `app/schemas.py` -- added `UserCreate`/`UserOut`/`Token`; added an optional `user_id`
  field to `PatientCreate`; added `model_config = {"from_attributes": True}` to the
  schemas now built directly from ORM rows.
- `app/routers/patients.py`, `app/routers/vital_signs.py`, `app/routers/activity.py` --
  rewired from the Phase 2 in-memory lists to real database queries (via `app/services.py`),
  behind authentication and RBAC, with audit logging and (for vital signs/activity data)
  `start`/`end` date-range filtering added. **Endpoint URL shapes and response models are
  unchanged from Phase 2** -- only what's inside each route changed.
- `requirements.txt` -- added `alembic`, `pyjwt`, `bcrypt`, `python-multipart`, `pytest`,
  `pytest-cov`, `httpx`, `pydantic-settings`.
- `pyproject.toml` -- added `[tool.pytest.ini_options]` so `pytest` resolves imports correctly.
- `DBSchema.sql` -- sample seed users now have a real bcrypt password hash (`welcome@123`
  for all of them) instead of placeholder strings, so they can actually log in.
- `API-Documentation.json` -- refreshed snapshot of `/openapi.json`, now including the
  `auth` endpoints and the `OAuth2PasswordBearer` security scheme.
- `README.md` -- rewritten for Phase 3 (this file); the previous version is preserved at
  `README-Phase2.md`.

**Unchanged (still Phase 2 in-memory stubs -- Phase 4/5 scope):**

- `app/routers/alert_thresholds.py`, `app/routers/alerts.py`, `app/routers/risk_scores.py`.

- Real PostgreSQL persistence via SQLAlchemy (`app/models.py`) for patients,
  vital signs, and activity data, replacing the Phase 2 in-memory lists.
  Users/providers/alert-thresholds/alerts/risk-scores are modeled too (for
  schema completeness and Alembic), but only patients/vitals/activity/auth
  get live CRUD wiring this phase.
- Data access/service layer in `app/services.py`: create/get/list/update/delete per
  resource, with date-range + pagination filtering, `IntegrityError`
  handling, and logging.
- JWT authentication (`app/auth.py`, `app/routers/auth.py`): register/login,
  bcrypt password hashing, role-based access control (`patient` sees only
  their own records; `provider`/`admin` see any patient; `it_staff` sees no
  clinical data).
- `audit_log` writes on every create/update/delete and single-record read
  against patient-facing data.
- Alembic migrations (`alembic/versions/`): one revision for the core
  identity tables (users, providers, patients), a second for everything that
  hangs off a patient (vital signs, activity data, alert thresholds, alerts,
  risk scores, audit log). `app.database.ensure_database_exists()` creates
  the database itself first (run automatically from the app's startup
  lifespan, and also available as a standalone step via
  `scripts/create_database.py`), since Alembic can't do that as one of its
  own migrations.
- 45 pytest tests (`app/tests/`) covering model constraints/FK relationships,
  auth, RBAC, and CRUD for patients/vital-signs/activity-data, run against
  the real database with per-test rollback. 91% overall coverage.
- `HealthTrackerApp.postman_collection.json` -- register/login (saves the
  bearer token automatically) plus CRUD requests for every Phase 3 endpoint.

### Key changes

#### 1. Endpoints added

**Auth**

- `POST /auth/register` -- Create a login account.
- `POST /auth/login` -- Exchange credentials for a bearer token.

**Patients / Vital Signs / Activity Data**

- Same URL shapes as Phase 2 (`POST`/`GET`/`GET {id}`/`PUT`/`DELETE` on
  `/patients/`; `POST`/`GET`/`GET {id}` on `/vital-signs/` and
  `/activity-data/`), now backed by Postgres, behind auth, and with
  `start`/`end` date-range query params added to the vital-signs and
  activity-data list endpoints.

#### 2. No more in-memory storage (for these three resources)

`app/services.py` replaces the old `_patients`/`_vital_signs`/`_activity_data`
module-level lists with real queries against the database, through a
`db: Session = Depends(get_db)` dependency on every route.

#### 3. Auth and RBAC

- Every route except `/auth/*` now requires `Authorization: Bearer <token>`.
- `patient` role is restricted to their own records; `provider`/`admin` can
  reach any patient; `it_staff` gets 403 on all clinical-data routes.

#### 4. Still in-memory (Phase 4/5 scope)

`alert_thresholds`, `alerts`, and `risk_scores` routers are untouched --
same in-memory lists as Phase 2, since the rule engine and risk-scoring model
that would populate them are Phase 4 and Phase 5 work respectively.
