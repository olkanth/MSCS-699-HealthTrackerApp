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

# ------------------------
# Error response schema
# ------------------------
class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Patient not found."])