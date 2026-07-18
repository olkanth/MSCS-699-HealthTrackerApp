# --------------------------------------
# /vital-signs CRUD, RBAC, and date-range filtering tests.
# --------------------------------------

from datetime import datetime, timedelta

from app.tests.conftest import auth_headers


# Shared setup: create a patient profile for the given (already-authenticated) user, return its id.
def _make_patient(client, headers, mrn):
    r = client.post(
        "/patients/",
        json={"first_name": "A", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": mrn},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# Round-trips a reading through the "120/80" blood_pressure string ->
# systolic_bp/diastolic_bp columns -> back to "120/80" conversion in services.py.
def test_create_and_get_vital_signs(client):
    _, alice_headers = auth_headers(client, "vsalice1", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-VSA-001")

    r = client.post(
        "/vital-signs/",
        json={"patient_id": patient_id, "heart_rate": 75, "blood_pressure": "120/80", "temperature": 98.6},
        headers=alice_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["blood_pressure"] == "120/80"
    vs_id = body["id"]

    r = client.get(f"/vital-signs/{vs_id}", headers=alice_headers)
    assert r.status_code == 200
    assert r.json()["heart_rate"] == 75


# blood_pressure has to parse as "systolic/diastolic"; a string that doesn't
# split into two integers is rejected as a 422 (ValidationError in services.py).
def test_vital_signs_invalid_blood_pressure_format(client):
    _, alice_headers = auth_headers(client, "vsalice2", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-VSA-002")

    r = client.post(
        "/vital-signs/",
        json={"patient_id": patient_id, "blood_pressure": "not-a-bp"},
        headers=alice_headers,
    )
    assert r.status_code == 422


# heart_rate has a ge=20/le=300 constraint on the Pydantic schema, so an
# out-of-range value is caught there and never reaches Postgres's own CHECK constraint.
def test_vital_signs_heart_rate_out_of_range_rejected_before_db(client):
    _, alice_headers = auth_headers(client, "vsalice3", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-VSA-003")

    r = client.post("/vital-signs/", json={"patient_id": patient_id, "heart_rate": 999}, headers=alice_headers)
    assert r.status_code == 422  # caught by the Pydantic ge/le constraint, never reaches Postgres


# RBAC ownership check: a patient can't record vitals against another patient's patient_id.
def test_vital_signs_cross_patient_forbidden(client):
    _, alice_headers = auth_headers(client, "vsalice4", "patient")
    _, bob_headers = auth_headers(client, "vsbob4", "patient")
    bob_patient_id = _make_patient(client, bob_headers, "MRN-VSB-004")

    r = client.post("/vital-signs/", json={"patient_id": bob_patient_id, "heart_rate": 70}, headers=alice_headers)
    assert r.status_code == 403


# A reading recorded now shouldn't show up when filtering start= to a
# future timestamp -- proves the start filter is actually applied.
def test_vital_signs_date_range_filter_excludes_out_of_range(client):
    _, alice_headers = auth_headers(client, "vsalice5", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-VSA-005")
    client.post("/vital-signs/", json={"patient_id": patient_id, "heart_rate": 60}, headers=alice_headers)

    future_start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    r = client.get(f"/vital-signs/?patient_id={patient_id}&start={future_start}", headers=alice_headers)
    assert r.status_code == 200
    assert r.json() == []


# The flip side of the previous test: a reading recorded now does show up
# when filtering start= to a past timestamp.
def test_vital_signs_date_range_filter_includes_in_range(client):
    _, alice_headers = auth_headers(client, "vsalice7", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-VSA-007")
    client.post("/vital-signs/", json={"patient_id": patient_id, "heart_rate": 60}, headers=alice_headers)

    past_start = (datetime.utcnow() - timedelta(days=1)).isoformat()
    r = client.get(f"/vital-signs/?patient_id={patient_id}&start={past_start}", headers=alice_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


# Looking up a vital_signs_id that was never created returns 404.
def test_get_nonexistent_vital_signs_404(client):
    _, alice_headers = auth_headers(client, "vsalice6", "patient")
    r = client.get("/vital-signs/999999", headers=alice_headers)
    assert r.status_code == 404
