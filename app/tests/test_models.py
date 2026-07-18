# --------------------------------------
# Model-level tests: field constraints, FK relationships, invalid data.
# These exercise the real Postgres CHECK/FK constraints, not just Pydantic.
# --------------------------------------

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app import models


# Shared setup: insert a bare-minimum user row directly via the ORM.
def make_user(db_session, username, role="patient"):
    user = models.User(username=username, email=f"{username}@example.com", password_hash="x", role=role)
    db_session.add(user)
    db_session.commit()
    return user


# Shared setup: insert a bare-minimum patient row linked to the given user.
def make_patient(db_session, user, mrn):
    patient = models.Patient(
        user_id=user.id, first_name="Test", last_name="Patient", date_of_birth=date(1990, 1, 1), mrn=mrn
    )
    db_session.add(patient)
    db_session.commit()
    return patient


# users.role has a CHECK constraint restricting it to patient/provider/admin/it_staff.
def test_user_role_check_constraint_rejects_unknown_role(db_session):
    user = models.User(username="bad_role", email="bad_role@example.com", password_hash="x", role="not_a_role")
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.commit()


# patients.user_id is a foreign key to users.id; a user_id that doesn't exist is rejected.
def test_patient_requires_valid_user_fk(db_session):
    patient = models.Patient(
        user_id=999_999, first_name="No", last_name="User", date_of_birth=date(1990, 1, 1), mrn="MRN-FK-1"
    )
    db_session.add(patient)
    with pytest.raises(IntegrityError):
        db_session.commit()


# patients has a CHECK constraint that date_of_birth can't be in the future.
def test_patient_dob_in_future_rejected(db_session):
    user = make_user(db_session, "futureuser")
    patient = models.Patient(
        user_id=user.id,
        first_name="Future",
        last_name="Baby",
        date_of_birth=date.today() + timedelta(days=365),
        mrn="MRN-FUT-1",
    )
    db_session.add(patient)
    with pytest.raises(IntegrityError):
        db_session.commit()


# patients.mrn is UNIQUE; two different patients can't share the same MRN.
def test_duplicate_mrn_rejected(db_session):
    user1 = make_user(db_session, "dupuser1")
    user2 = make_user(db_session, "dupuser2")
    make_patient(db_session, user1, "MRN-DUP-1")

    dup_patient = models.Patient(
        user_id=user2.id, first_name="Dup", last_name="licate", date_of_birth=date(1990, 1, 1), mrn="MRN-DUP-1"
    )
    db_session.add(dup_patient)
    with pytest.raises(IntegrityError):
        db_session.commit()


# vital_signs has a CHECK constraint that heart_rate stays within 20-300 bpm.
def test_vital_signs_heart_rate_out_of_range_rejected(db_session):
    user = make_user(db_session, "vsuser1")
    patient = make_patient(db_session, user, "MRN-VS-1")
    vs = models.VitalSigns(patient_id=patient.id, heart_rate=500, recorded_at=datetime.utcnow())
    db_session.add(vs)
    with pytest.raises(IntegrityError):
        db_session.commit()


# vital_signs has a CHECK constraint that systolic_bp must be greater than diastolic_bp.
def test_vital_signs_systolic_must_exceed_diastolic(db_session):
    user = make_user(db_session, "vsuser2")
    patient = make_patient(db_session, user, "MRN-VS-2")
    vs = models.VitalSigns(patient_id=patient.id, systolic_bp=80, diastolic_bp=90, recorded_at=datetime.utcnow())
    db_session.add(vs)
    with pytest.raises(IntegrityError):
        db_session.commit()


# vital_signs has a CHECK constraint that spo2 stays within 0-100 (a percentage).
def test_vital_signs_spo2_out_of_range_rejected(db_session):
    user = make_user(db_session, "vsuser3")
    patient = make_patient(db_session, user, "MRN-VS-3")
    vs = models.VitalSigns(patient_id=patient.id, spo2=150, recorded_at=datetime.utcnow())
    db_session.add(vs)
    with pytest.raises(IntegrityError):
        db_session.commit()


# activity_data has a CHECK constraint that steps can't be negative.
def test_activity_data_negative_steps_rejected(db_session):
    user = make_user(db_session, "actuser1")
    patient = make_patient(db_session, user, "MRN-ACT-1")
    act = models.ActivityData(patient_id=patient.id, steps=-5, recorded_at=datetime.utcnow())
    db_session.add(act)
    with pytest.raises(IntegrityError):
        db_session.commit()


# Patient.vital_signs (the SQLAlchemy relationship) reflects rows actually
# inserted with that patient_id, once the session is refreshed.
def test_patient_relationship_loads_vital_signs(db_session):
    user = make_user(db_session, "reluser1")
    patient = make_patient(db_session, user, "MRN-REL-1")
    vs = models.VitalSigns(patient_id=patient.id, heart_rate=70, recorded_at=datetime.utcnow())
    db_session.add(vs)
    db_session.commit()

    db_session.refresh(patient)
    assert len(patient.vital_signs) == 1
    assert patient.vital_signs[0].heart_rate == 70


# vital_signs.patient_id is declared ondelete="CASCADE", so deleting a
# patient also deletes their vital signs rather than leaving orphaned rows.
def test_deleting_patient_cascades_to_vital_signs(db_session):
    user = make_user(db_session, "cascadeuser1")
    patient = make_patient(db_session, user, "MRN-CASCADE-1")
    vs = models.VitalSigns(patient_id=patient.id, heart_rate=70, recorded_at=datetime.utcnow())
    db_session.add(vs)
    db_session.commit()
    vs_id = vs.id

    db_session.delete(patient)
    db_session.commit()

    assert db_session.query(models.VitalSigns).filter(models.VitalSigns.id == vs_id).first() is None
