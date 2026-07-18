# --------------------------------------
# Script to perform baseline performance measurement 
# --------------------------------------

from _pytest import pytester_assertions
import statistics
import sys
import time
from pathlib import Path

# Allow running this file directly (`python scripts/performance_check.py`)
# without installing the project as a package: put the repo root on
# sys.path so `app` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.config import settings
from app.database import engine
from app.main import app

N_REQUESTS = 100  # how many times each endpoint is hit to build a timing sample


def time_requests(client: TestClient, method: str, url: str, **kwargs) -> list[float]:
    # Fire the same request N_REQUESTS times and return each round-trip
    # duration in milliseconds, for summarize() to turn into stats.
    durations = []
    for _ in range(N_REQUESTS):
        start = time.perf_counter()
        client.request(method, url, **kwargs)
        durations.append((time.perf_counter() - start) * 1000)  # ms
    return durations


def summarize(label: str, durations: list[float]) -> None:
    # Print mean/median/p95/max for one endpoint's timing sample.
    print(f"{label}: n={len(durations)} "
          f"mean={statistics.mean(durations):.2f}ms "
          f"median={statistics.median(durations):.2f}ms "
          f"p95={sorted(durations)[int(len(durations) * 0.95) - 1]:.2f}ms "
          f"max={max(durations):.2f}ms")


def run_timing_check() -> None:
    # Log in (registering a throwaway account first if it doesn't exist yet)
    # so the timed requests below are authenticated like real traffic, then
    # time a handful of representative list/get endpoints.
    with TestClient(app) as client:
        r = client.post(
            "/auth/register",
            json={"username": "perfcheck_user3", "email": "perfcheck3@example.com", "password": "perfcheck123", "role": "provider"},
        )
        if r.status_code not in (201, 409):
            print("Setup failed:", r.status_code, r.text)
            return
        r = client.post("/auth/login", data={"username": "perfcheck_user3", "password": "perfcheck123"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        print(f"\n--- Baseline timing ({N_REQUESTS} requests each, in-process, no network hop) ---")
        summarize("GET /patients/ (list, paginated)", time_requests(client, "GET", "/patients/?limit=20", headers=headers))
        summarize("GET /patients/1 (single record)", time_requests(client, "GET", "/patients/1", headers=headers))
        summarize(
            "GET /vital-signs/?patient_id=1 (filtered list)",
            time_requests(client, "GET", "/vital-signs/?patient_id=1", headers=headers),
        )


def run_explain_analyze() -> None:
    # Run the same patient+date-range query the vital-signs list endpoint
    # uses, through Postgres's own EXPLAIN ANALYZE, to confirm it actually
    # uses idx_vitals_patient_time (an index scan) rather than a full table scan.
    print("\n--- EXPLAIN ANALYZE: vital signs for one patient, date-range filtered ---")
    query = """
        EXPLAIN ANALYZE
        SELECT * FROM vital_signs
        WHERE patient_id = 1 AND recorded_at >= NOW() - INTERVAL '30 days'
        ORDER BY recorded_at DESC
        LIMIT 50;
    """
    with engine.connect() as conn:
        result = conn.exec_driver_sql(query)
        for row in result:
            print("-"*50)
            print(row[0])


if __name__ == "__main__":
    print(f"Database: {settings.database_url.split('@')[-1]}")  # host/db only, no credentials
    print("NOTE: this is a baseline measurement for the Phase 3 report, not optimization work --")
    print("bottleneck analysis and tuning are Phase 6 (Performance Optimization) scope.\n")
    run_timing_check()
    run_explain_analyze()
