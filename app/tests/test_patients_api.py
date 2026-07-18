# --------------------------------------
# /patients CRUD + RBAC tests, driven through the HTTP API (TestClient).
# --------------------------------------

from app.tests.conftest import auth_headers


# A patient can create their own profile (no user_id needed -- it defaults
# to their own account) and then read it back.
def test_patient_self_service_create_and_read(client):
    _, alice_headers = auth_headers(client, "alice1", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "Alice", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-T-001"},
        headers=alice_headers,
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    r = client.get(f"/patients/{patient_id}", headers=alice_headers)
    assert r.status_code == 200
    assert r.json()["mrn"] == "MRN-T-001"


# RBAC ownership check: a patient can't read a different patient's profile.
def test_patient_cannot_read_another_patient(client):
    _, alice_headers = auth_headers(client, "alice2", "patient")
    _, bob_headers = auth_headers(client, "bob2", "patient")

    r = client.post(
        "/patients/",
        json={"first_name": "Bob", "last_name": "B", "date_of_birth": "1985-01-01", "mrn": "MRN-T-002"},
        headers=bob_headers,
    )
    bob_patient_id = r.json()["id"]

    r = client.get(f"/patients/{bob_patient_id}", headers=alice_headers)
    assert r.status_code == 403


# A provider onboarding a patient on their behalf must supply user_id, and
# that's allowed even though the caller isn't the account being linked.
def test_provider_can_create_patient_for_specific_user(client):
    user_id, _ = auth_headers(client, "carol3", "patient")
    _, provider_headers = auth_headers(client, "dr3", "provider")

    r = client.post(
        "/patients/",
        json={
            "first_name": "Carol",
            "last_name": "C",
            "date_of_birth": "1975-01-01",
            "mrn": "MRN-T-003",
            "user_id": user_id,
        },
        headers=provider_headers,
    )
    assert r.status_code == 201


# A provider/admin caller must supply user_id (there's no "self" to default
# to); omitting it is a 422, not a silent guess.
def test_provider_create_patient_missing_user_id_rejected(client):
    _, provider_headers = auth_headers(client, "dr4", "provider")
    r = client.post(
        "/patients/",
        json={"first_name": "NoLink", "last_name": "C", "date_of_birth": "1975-01-01", "mrn": "MRN-T-004"},
        headers=provider_headers,
    )
    assert r.status_code == 422


# it_staff has no clinical-data access at all (minimum-necessary principle),
# so even creating a patient profile is forbidden.
def test_it_staff_cannot_create_patient(client):
    _, staff_headers = auth_headers(client, "itstaff5", "it_staff")
    r = client.post(
        "/patients/",
        json={"first_name": "X", "last_name": "Y", "date_of_birth": "1975-01-01", "mrn": "MRN-T-005"},
        headers=staff_headers,
    )
    assert r.status_code == 403


# Listing every patient is provider/admin only; a patient-role token gets 403.
def test_patient_list_forbidden_for_patient_role(client):
    _, alice_headers = auth_headers(client, "alice6", "patient")
    r = client.get("/patients/", headers=alice_headers)
    assert r.status_code == 403


# The flip side of the previous test: a provider-role token can list everyone.
def test_provider_can_list_patients(client):
    _, provider_headers = auth_headers(client, "dr7", "provider")
    r = client.get("/patients/", headers=provider_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# Looking up a patient_id that was never created returns 404.
def test_get_nonexistent_patient_404(client):
    _, provider_headers = auth_headers(client, "dr8", "provider")
    r = client.get("/patients/999999", headers=provider_headers)
    assert r.status_code == 404


# patients.mrn is UNIQUE at the DB level; two different patients (different
# accounts) sharing the same MRN surfaces as a 409 through the API, not a 500.
def test_duplicate_mrn_conflict(client):
    _, alice_headers = auth_headers(client, "alice9", "patient")
    _, bob_headers = auth_headers(client, "bob9", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "A", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-T-DUPE"},
        headers=alice_headers,
    )
    assert r.status_code == 201
    r = client.post(
        "/patients/",
        json={"first_name": "B", "last_name": "B", "date_of_birth": "1990-01-01", "mrn": "MRN-T-DUPE"},
        headers=bob_headers,
    )
    assert r.status_code == 409


# A patient can PUT changes to their own profile and see them reflected.
def test_patient_can_update_own_profile(client):
    _, alice_headers = auth_headers(client, "alice11", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "Alice", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-T-011"},
        headers=alice_headers,
    )
    patient_id = r.json()["id"]

    r = client.put(
        f"/patients/{patient_id}",
        json={"first_name": "Alicia", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-T-011"},
        headers=alice_headers,
    )
    assert r.status_code == 200
    assert r.json()["first_name"] == "Alicia"


# DELETE is provider/admin only, not self-service: a patient's own token
# gets 403 on their own profile, but a provider token succeeds (204).
def test_delete_patient_requires_provider(client):
    _, alice_headers = auth_headers(client, "alice10", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "A", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-T-010"},
        headers=alice_headers,
    )
    patient_id = r.json()["id"]

    r = client.delete(f"/patients/{patient_id}", headers=alice_headers)
    assert r.status_code == 403

    _, provider_headers = auth_headers(client, "dr10", "provider")
    r = client.delete(f"/patients/{patient_id}", headers=provider_headers)
    assert r.status_code == 204
