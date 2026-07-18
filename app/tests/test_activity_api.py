# --------------------------------------
# /activity-data CRUD and RBAC tests.
# --------------------------------------

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


# A patient can record an activity entry for themselves and see it come
# back from the list endpoint for their own patient_id.
def test_create_and_list_activity_data(client):
    _, alice_headers = auth_headers(client, "actalice1", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-ACT-001")

    r = client.post(
        "/activity-data/",
        json={"patient_id": patient_id, "steps": 5000, "active_minutes": 30},
        headers=alice_headers,
    )
    assert r.status_code == 201

    r = client.get(f"/activity-data/?patient_id={patient_id}", headers=alice_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["steps"] == 5000


# steps has a ge=0 constraint on the Pydantic schema, so a negative value is
# rejected as a 422 validation error before it ever reaches the DB.
def test_activity_data_negative_steps_rejected_by_schema(client):
    _, alice_headers = auth_headers(client, "actalice2", "patient")
    patient_id = _make_patient(client, alice_headers, "MRN-ACT-002")

    r = client.post("/activity-data/", json={"patient_id": patient_id, "steps": -10}, headers=alice_headers)
    assert r.status_code == 422


# RBAC ownership check: a patient can't record activity data against another
# patient's patient_id, even though both accounts have role "patient".
def test_activity_cross_patient_forbidden(client):
    _, alice_headers = auth_headers(client, "actalice3", "patient")
    _, bob_headers = auth_headers(client, "actbob3", "patient")
    bob_patient_id = _make_patient(client, bob_headers, "MRN-ACTB-003")

    r = client.post("/activity-data/", json={"patient_id": bob_patient_id, "steps": 100}, headers=alice_headers)
    assert r.status_code == 403


# Looking up an activity_id that was never created returns 404, not a 500 or empty 200.
def test_get_nonexistent_activity_404(client):
    _, alice_headers = auth_headers(client, "actalice4", "patient")
    r = client.get("/activity-data/999999", headers=alice_headers)
    assert r.status_code == 404
