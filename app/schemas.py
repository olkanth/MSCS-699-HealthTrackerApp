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



class ErrorResponse(BaseModel):
    detail: str = Field(..., examples=["Patient not found."])