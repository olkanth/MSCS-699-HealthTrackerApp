from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Query, Path   

from .. import schemas


router = APIRouter(prefix="/patients", tags=["Patients"])

# In-memory store, skeleton/demo only -- not persisted
# replaced by SQLAlchemy with PostgreSQL in Phase 3.
_patients: List[schemas.Patient] = []
_next_id = 1

@router.post(
    "/",
    response_model=schemas.Patient,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)
async def create_patient(patient: schemas.PatientCreate):
    """Create a new patient profile."""
    global _next_id
    new_patient = schemas.Patient(id=_next_id, created_at=datetime.now(timezone.utc), **patient.dict())
    _patients.append(new_patient)
    _next_id += 1
    return new_patient


@router.get("/", response_model=List[schemas.Patient])
async def list_patients(limit: int = 20, offset: int = 0):
    """List patients, with basic pagination."""
    return _patients[offset: offset + limit]


@router.get(
    "/{patient_id}",
    response_model=schemas.Patient,
    responses={404: {"model": schemas.ErrorResponse, "description": "Patient not found"}},
)
async def get_patient(patient_id: int = Path(..., description="ID of the patient to retrieve")):
    """Get a single patient's profile by id."""
    for p in _patients:
        if p.id == patient_id:
            return p
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")


@router.put(
    "/{patient_id}",
    response_model=schemas.Patient,
    responses={404: {"model": schemas.ErrorResponse, "description": "Patient not found"}},
)
async def update_patient(patient: schemas.PatientCreate, patient_id: int = Path(..., description="ID of the patient to update")):
    """Update a patient's profile."""
    for i, p in enumerate(_patients):
        if p.id == patient_id:
            updated = schemas.Patient(id=patient_id, created_at=p.created_at, **patient.dict())
            _patients[i] = updated
            return updated
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": schemas.ErrorResponse, "description": "Patient not found"}},
)
async def delete_patient(patient_id: int = Path(..., description="ID of the patient to delete") ):
    """Delete a patient profile."""
    for i, p in enumerate(_patients):
        if p.id == patient_id:
            _patients.pop(i)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
