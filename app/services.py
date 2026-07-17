# --------------------------------------
# Data access layer -- the only place that talks to the database directly.
#
# Endpoints/Routers call these functions  to query the databases instead of building queries themselves, 
# and get back either an app/models.py ORM row (or list of rows).
# --------------------------------------

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a lookup by id finds no matching row."""


class DuplicateError(Exception):
    """Raised when a write would violate a uniqueness constraint."""


class ValidationError(Exception):
    """Raised when input is well-formed JSON but semantically invalid (e.g. malformed blood_pressure)."""


def _utcnow() -> datetime:
    """Naive UTC "now", matching the naive TIMESTAMP columns in the DB (no tzinfo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
def create_user(db: Session, *, username: str, email: str, password_hash: str, role: str) -> models.User:
    user = models.User(username=username, email=email, password_hash=password_hash, role=role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("create_user failed, duplicate username/email: %s", username)
        raise DuplicateError(f"Username '{username}' or email '{email}' is already registered.") from exc
    db.refresh(user)
    logger.info("Created user id=%s username=%s role=%s", user.id, user.username, user.role)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


# ---------------------------------------------------------------------
# Patients
# ---------------------------------------------------------------------
def create_patient(db: Session, patient_in: schemas.PatientCreate, user_id: int) -> models.Patient:
    patient = models.Patient(
        user_id=user_id,
        first_name=patient_in.first_name,
        last_name=patient_in.last_name,
        date_of_birth=patient_in.date_of_birth,
        mrn=patient_in.mrn,
    )
    db.add(patient)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("create_patient failed, duplicate mrn or user_id already linked: %s", patient_in.mrn)
        raise DuplicateError(
            f"MRN '{patient_in.mrn}' is already in use, or this user account is already linked to a patient."
        ) from exc
    db.refresh(patient)
    logger.info("Created patient id=%s mrn=%s", patient.id, patient.mrn)
    return patient


def get_patient(db: Session, patient_id: int) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()


def get_patient_by_user_id(db: Session, user_id: int) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def list_patients(db: Session, limit: int = 20, offset: int = 0) -> list[models.Patient]:
    return db.query(models.Patient).order_by(models.Patient.id).offset(offset).limit(limit).all()


def update_patient(db: Session, patient_id: int, patient_in: schemas.PatientCreate) -> models.Patient:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found.")
    patient.first_name = patient_in.first_name
    patient.last_name = patient_in.last_name
    patient.date_of_birth = patient_in.date_of_birth
    patient.mrn = patient_in.mrn
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateError(f"MRN '{patient_in.mrn}' is already in use.") from exc
    db.refresh(patient)
    logger.info("Updated patient id=%s", patient.id)
    return patient


def delete_patient(db: Session, patient_id: int) -> None:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found.")
    db.delete(patient)
    db.commit()
    logger.info("Deleted patient id=%s", patient_id)


# ---------------------------------------------------------------------
# Vital signs
# ---------------------------------------------------------------------
def _parse_blood_pressure(blood_pressure: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """'120/80' -> (120, 80); None -> (None, None)."""
    if blood_pressure is None:
        return None, None
    try:
        systolic_str, diastolic_str = blood_pressure.split("/")
        return int(systolic_str), int(diastolic_str)
    except (ValueError, AttributeError) as exc:
        raise ValidationError(
            f"blood_pressure must be formatted as 'systolic/diastolic' (e.g. '120/80'), got {blood_pressure!r}."
        ) from exc


def _format_blood_pressure(systolic: Optional[int], diastolic: Optional[int]) -> Optional[str]:
    if systolic is None or diastolic is None:
        return None
    return f"{systolic}/{diastolic}"


def _vital_signs_to_schema(row: models.VitalSigns) -> schemas.VitalSigns:
    return schemas.VitalSigns(
        id=row.id,
        patient_id=row.patient_id,
        heart_rate=row.heart_rate,
        blood_pressure=_format_blood_pressure(row.systolic_bp, row.diastolic_bp),
        temperature=float(row.temperature) if row.temperature is not None else None,
        recorded_at=row.recorded_at,
    )


def create_vital_signs(db: Session, vitals_in: schemas.VitalSignsCreate) -> schemas.VitalSigns:
    systolic, diastolic = _parse_blood_pressure(vitals_in.blood_pressure)
    row = models.VitalSigns(
        patient_id=vitals_in.patient_id,
        heart_rate=vitals_in.heart_rate,
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        temperature=vitals_in.temperature,
        recorded_at=_utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("create_vital_signs failed for patient_id=%s", vitals_in.patient_id)
        raise NotFoundError(f"Patient {vitals_in.patient_id} not found.") from exc
    db.refresh(row)
    logger.info("Recorded vital signs id=%s for patient_id=%s", row.id, row.patient_id)
    return _vital_signs_to_schema(row)


def get_vital_signs(db: Session, vital_signs_id: int) -> Optional[schemas.VitalSigns]:
    row = db.query(models.VitalSigns).filter(models.VitalSigns.id == vital_signs_id).first()
    return _vital_signs_to_schema(row) if row else None


def list_vital_signs(
    db: Session,
    patient_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[schemas.VitalSigns]:
    query = db.query(models.VitalSigns).filter(models.VitalSigns.patient_id == patient_id)
    if start is not None:
        query = query.filter(models.VitalSigns.recorded_at >= start)
    if end is not None:
        query = query.filter(models.VitalSigns.recorded_at <= end)
    rows = query.order_by(models.VitalSigns.recorded_at.desc()).offset(offset).limit(limit).all()
    return [_vital_signs_to_schema(row) for row in rows]


# ---------------------------------------------------------------------
# Activity data
# ---------------------------------------------------------------------
def create_activity_data(db: Session, activity_in: schemas.ActivityDataCreate) -> models.ActivityData:
    row = models.ActivityData(
        patient_id=activity_in.patient_id,
        steps=activity_in.steps,
        active_minutes=activity_in.active_minutes,
        recorded_at=_utcnow(),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("create_activity_data failed for patient_id=%s", activity_in.patient_id)
        raise NotFoundError(f"Patient {activity_in.patient_id} not found.") from exc
    db.refresh(row)
    logger.info("Recorded activity data id=%s for patient_id=%s", row.id, row.patient_id)
    return row


def get_activity_data(db: Session, activity_id: int) -> Optional[models.ActivityData]:
    return db.query(models.ActivityData).filter(models.ActivityData.id == activity_id).first()


def list_activity_data(
    db: Session,
    patient_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[models.ActivityData]:
    query = db.query(models.ActivityData).filter(models.ActivityData.patient_id == patient_id)
    if start is not None:
        query = query.filter(models.ActivityData.recorded_at >= start)
    if end is not None:
        query = query.filter(models.ActivityData.recorded_at <= end)
    return query.order_by(models.ActivityData.recorded_at.desc()).offset(offset).limit(limit).all()


# ---------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------
def log_action(db: Session, user_id: Optional[int], action: str, table_name: str, record_id: int) -> None:
    """Best-effort audit trail write; logs and swallows failures rather than
    failing the request that triggered it."""
    entry = models.AuditLog(user_id=user_id, action=action, table_name=table_name, record_id=record_id)
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.exception(
            "Failed to write audit log entry: user_id=%s action=%s table=%s record_id=%s",
            user_id, action, table_name, record_id,
        )
