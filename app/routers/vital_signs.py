from app.routers.patients import _patients
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Query, Path   

from .. import schemas


# ------------------------
# Vital signs router
# ------------------------
router = APIRouter(prefix="/vital-signs", tags=["Vital Signs"])

# In-memory store, skeleton/demo only -- not persisted
# replaced by SQLAlchemy with PostgreSQL in Phase 3.
_vital_signs: List[schemas.VitalSigns] = []
_next_id = 1

@router.post(
    "/",
    response_model=schemas.VitalSigns,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)

# Create vital sign reading
async def create_vital_signs(vital_signs: schemas.VitalSignsCreate):
    """Record a new vital sign reading."""
    global _next_id
    new_record = schemas.VitalSigns(id=_next_id, recorded_at=datetime.now(timezone.utc), **vital_signs.dict())
    _vital_signs.append(new_record)
    _next_id += 1
    return new_record


# Get vital sign reading by id
@router.get(
    "/{vital_signs_id}",
    response_model=schemas.VitalSigns,
    responses={404: {"model": schemas.ErrorResponse, "description": "Reading not found"}},
)
async def get_vital_signs(vital_signs_id: int = Path(..., description="ID of the vital sign reading to retrieve")):
    """Get a single vital sign reading by id."""
    for record in _vital_signs:
        if record.id == vital_signs_id:
            return record
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vital sign reading not found.")


# List vital sign readings for a patient
@router.get("/", response_model=List[schemas.VitalSigns])
async def list_vital_signs(
    patient_id: int = Query(..., description="ID of the patient whose vital signs to retrieve"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip, for pagination"),
):
    """List vital sign readings for a patient, most recent first."""
    matches = [r for r in _vital_signs if r.patient_id == patient_id]
    matches.sort(key=lambda r: r.recorded_at, reverse=True)
    return matches[offset: offset + limit]
