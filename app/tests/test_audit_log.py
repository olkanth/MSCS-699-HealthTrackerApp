# --------------------------------------
# Confirms audit_log rows get written on create/read (not on list) actions.
# --------------------------------------

from app import models
from app.tests.conftest import auth_headers


# Creating a patient and then reading it back should each write their own
# audit_log row (action="create" and action="read") against that patient_id.
def test_audit_log_written_on_patient_create_and_read(client, db_session):
    _, alice_headers = auth_headers(client, "audalice1", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "A", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-AUD-001"},
        headers=alice_headers,
    )
    patient_id = r.json()["id"]

    client.get(f"/patients/{patient_id}", headers=alice_headers)

    rows = (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.table_name == "patients", models.AuditLog.record_id == patient_id)
        .order_by(models.AuditLog.id)
        .all()
    )
    actions = [row.action for row in rows]
    assert "create" in actions
    assert "read" in actions


# Same audit-on-write check, for a different resource (vital_signs).
def test_audit_log_written_on_vital_signs_create(client, db_session):
    _, alice_headers = auth_headers(client, "audalice2", "patient")
    r = client.post(
        "/patients/",
        json={"first_name": "A", "last_name": "A", "date_of_birth": "1990-01-01", "mrn": "MRN-AUD-002"},
        headers=alice_headers,
    )
    patient_id = r.json()["id"]

    r = client.post("/vital-signs/", json={"patient_id": patient_id, "heart_rate": 65}, headers=alice_headers)
    vs_id = r.json()["id"]

    row = (
        db_session.query(models.AuditLog)
        .filter(models.AuditLog.table_name == "vital_signs", models.AuditLog.record_id == vs_id)
        .first()
    )
    assert row is not None
    assert row.action == "create"


# Paginated list endpoints are the deliberate exception: they don't write
# one audit_log row per item returned, so the count shouldn't change.
def test_audit_log_not_written_on_list_endpoints(client, db_session):
    _, provider_headers = auth_headers(client, "auddoc3", "provider")
    before_count = db_session.query(models.AuditLog).count()

    client.get("/patients/", headers=provider_headers)

    after_count = db_session.query(models.AuditLog).count()
    assert after_count == before_count
