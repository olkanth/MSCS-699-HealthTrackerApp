from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ------------------------
# Patients schemas
# ------------------------

class PatientBase(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    mrn: str = Field(..., description="Medical record number, e.g. MRN-00123")


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: int
    created_at: datetime


# ------------------------
# Vital signs schemas
# ------------------------
class VitalSignsCreate(BaseModel):
    patient_id: int
    heart_rate: Optional[int] = Field(None, ge=20, le=300, description="Beats per minute")
    blood_pressure: Optional[str] = Field(None, examples=["120/80"])
    temperature: Optional[float] = Field(None, description="Degrees Fahrenheit")


class VitalSigns(VitalSignsCreate):
    id: int
    recorded_at: datetime


# ---------------------------------------------------------------------
# Activity Data
# ---------------------------------------------------------------------
class ActivityDataCreate(BaseModel):
    patient_id: int
    steps: Optional[int] = Field(None, ge=0)
    active_minutes: Optional[int] = Field(None, ge=0)


class ActivityData(ActivityDataCreate):
    id: int
    recorded_at: datetime


# ---------------------------------------------------------------------
# Alert Thresholds (Phase 4: Alert System Implementation)
# ---------------------------------------------------------------------
class AlertThresholdCreate(BaseModel):
    patient_id: int
    metric_name: str = Field(..., examples=["heart_rate", "systolic_bp", "spo2"])
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class AlertThreshold(AlertThresholdCreate):
    id: int
    updated_at: datetime


# ---------------------------------------------------------------------
# Alerts (Phase 4: Alert System Implementation)
# ---------------------------------------------------------------------
class AlertCreate(BaseModel):
    patient_id: int
    metric_name: str
    value: float
    severity: str = Field(..., examples=["low", "medium", "high", "critical"])


class AlertUpdate(BaseModel):
    status: str = Field(..., examples=["acknowledged", "resolved"])
    acknowledged_by: Optional[int] = Field(None, description="User id of the staff member handling this alert")


class Alert(AlertCreate):
    id: int
    status: str = "open"
    triggered_at: datetime
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


# ---------------------------------------------------------------------
# Risk Scores (Phase 5: Risk Assessment System)
# ---------------------------------------------------------------------
class RiskScoreCreate(BaseModel):
    patient_id: int
    score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., examples=["low", "medium", "high"])
    contributing_factors: List[str] = Field(default_factory=list, examples=[["elevated systolic BP trend", "low activity level"]])


class RiskScore(RiskScoreCreate):
    id: int
    calculated_at: datetime

# ------------------------
# Error response schema
# ------------------------
class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Patient not found."])