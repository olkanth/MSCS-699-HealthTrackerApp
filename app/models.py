# --------------------------------------
# SQLAlchemy ORM models -- the database layer.
#
# These classes map directly to tables and are used for persistence 
# like querying/inserting rows  via a DB session. .
#
# Only Users, Patients, VitalSigns and ActivityData currently get live
# CRUD through router wiring. 
# Providers/AlertThreshold/Alert/RiskScore are modeled here for schema completeness and Alembic, 
# and get wired up once the alert engine and risk scoring logic that own them are implemented. 
# --------------------------------------

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


# ------------------------
# Users
# ------------------------
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('patient', 'provider', 'admin', 'it_staff')",
            name="chk_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="user", uselist=False)
    provider: Mapped["Provider"] = relationship(back_populates="user", uselist=False)


# ------------------------
# Providers
# ------------------------
class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(100))
    npi_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="provider")
    patients: Mapped[list["Patient"]] = relationship(back_populates="primary_provider")


# ------------------------
# Patients
# ------------------------
class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("date_of_birth <= CURRENT_DATE", name="chk_patients_dob"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(20))
    mrn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    primary_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="patient")
    primary_provider: Mapped["Provider"] = relationship(back_populates="patients")
    vital_signs: Mapped[list["VitalSigns"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    activity_data: Mapped[list["ActivityData"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    alert_thresholds: Mapped[list["AlertThreshold"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    risk_scores: Mapped[list["RiskScore"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


# ------------------------
# Vital signs
# ------------------------
class VitalSigns(Base):
    __tablename__ = "vital_signs"
    __table_args__ = (
        CheckConstraint("heart_rate IS NULL OR heart_rate BETWEEN 20 AND 300", name="chk_vitals_hr"),
        CheckConstraint("spo2 IS NULL OR spo2 BETWEEN 0 AND 100", name="chk_vitals_spo2"),
        CheckConstraint(
            "systolic_bp IS NULL OR diastolic_bp IS NULL OR systolic_bp > diastolic_bp",
            name="chk_vitals_bp",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger)
    systolic_bp: Mapped[int | None] = mapped_column(SmallInteger)
    diastolic_bp: Mapped[int | None] = mapped_column(SmallInteger)
    spo2: Mapped[int | None] = mapped_column(SmallInteger)
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 1))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), server_default="device")

    patient: Mapped["Patient"] = relationship(back_populates="vital_signs")


# ------------------------
# Activity data
# ------------------------
class ActivityData(Base):
    __tablename__ = "activity_data"
    __table_args__ = (
        CheckConstraint("steps IS NULL OR steps >= 0", name="chk_activity_steps"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    steps: Mapped[int | None] = mapped_column(Integer)
    active_minutes: Mapped[int | None] = mapped_column(Integer)
    distance_km: Mapped[float | None] = mapped_column(Numeric(5, 2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str | None] = mapped_column(String(50), server_default="device")

    patient: Mapped["Patient"] = relationship(back_populates="activity_data")


# ---------------------------------------------------------------------
# Alert thresholds
# ---------------------------------------------------------------------
class AlertThreshold(Base):
    __tablename__ = "alert_thresholds"
    __table_args__ = (
        UniqueConstraint("patient_id", "metric_name", name="uq_threshold_patient_metric"),
        CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value < max_value",
            name="chk_threshold_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    min_value: Mapped[float | None] = mapped_column(Numeric(6, 2))
    max_value: Mapped[float | None] = mapped_column(Numeric(6, 2))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="alert_thresholds")


# ---------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="chk_alert_severity"),
        CheckConstraint("status IN ('open', 'acknowledged', 'resolved')", name="chk_alert_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, server_default="open")
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    patient: Mapped["Patient"] = relationship(back_populates="alerts")


# ---------------------------------------------------------------------
# Risk scores
# ---------------------------------------------------------------------
class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="chk_risk_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    contributing_factors: Mapped[str | None] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="risk_scores")


# ---------------------------------------------------------------------
# Audit log -- HIPAA-style access/change log.
# ---------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("action IN ('create', 'read', 'update', 'delete')", name="chk_audit_action"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    table_name: Mapped[str] = mapped_column(String(50), nullable=False)
    record_id: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
