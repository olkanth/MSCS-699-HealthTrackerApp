# MSCS-699-HealthTrackerApp

FastAPI skeleton for the HealthTrack API (Project Phase 2): endpoints with
request/response Pydantic models, used to generate Swagger/OpenAPI docs.
No database or authentication yet (Phase 3) -- each endpoint uses simple
in-memory storage so it runs with zero setup.

## Run it (Ubuntu 24.04)

```bash
git clone https://github.com/olkanth/MSCS-699-HealthTrackerApp.git
cd MSCS-699-HealthTrackerApp

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

fastapi dev
```

Then open **http://localhost:8000/docs** for Swagger UI (no login needed).

**Note:** running `pip install` without the venv steps above fails on
Ubuntu 24.04 with `error: externally-managed-environment` -- create and
activate the venv first and it installs cleanly.

`API-Documentation.json` is a live snapshot of the same API
docs, pulled from a running instance, in case you just want the spec
without running the code.



# Phase 2 changes and review

- Added patient POST/GET and alerts POST/GET/PATCH.
- All endpoints use in-memory lists; no database yet.
- Added `/openapi.json` and `/redoc`.
- `API-Documentation.json` mirrors the running Swagger spec.

The app should now run with zero setup and produce the “Phase 2 API spec” you
need.

### Key changes

#### 1. Endpoints added

**Patients**

- `POST /patients/` – Create patient with validation.
- `GET /patients/` – List patients with optional limit/offset.
- `GET /patients/{patient_id}` – Get single patient with 404.

**Alerts**

- `POST /alerts/` – Create alert (triggered by rule engine in real Phase 3).
- `GET /alerts/` – List all alerts; supports `?patient_id=` and `?status=`
  filters.
- `GET /alerts/{alert_id}` – Get single alert with 404.
- `PATCH /alerts/{alert_id}` – Update status/acknowledge.

#### 2. In-memory storage

- `_patients: List[schemas.Patient]`
- `_alerts: List[schemas.Alert]`
- `_next_patient_id: int = 1`
- `_next_alert_id: int = 1`

Each endpoint adds/retrieves/updates the corresponding list; no persistence.

#### 3. API docs & metadata

- Added `tags` to endpoints so Swagger groups them into “Patients” / “Alerts”.
- Added descriptions, `operationId`, `requestBody`, and proper responses.
- The live `/openapi.json` should now look like the attached JSON.

#### 4. No auth / DB yet

- No JWT or auth middleware.
- No database, no SQLAlchemy, no migrations.

This is intentionally minimal so you can test the HTTP API shape and spec
without any setup.
