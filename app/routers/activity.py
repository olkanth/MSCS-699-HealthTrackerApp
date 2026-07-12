# ----------------------------------
# Activity routers
# ------------------------------------

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Query, Path
from .. import schemas

router = APIRouter(prefix="/activity-data", tags=["Activity"])

_activity_data: List[schemas.ActivityData] = []
_next_id = 1

# Route to create activity data
@router.post(
    "/",
    response_model=schemas.ActivityData,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)
async def create_activity_data(activity: schemas.ActivityDataCreate):
    """Record new activity data (steps, active minutes) for a patient."""
    global _next_id
    new_record = schemas.ActivityData(id=_next_id, recorded_at=datetime.now(timezone.utc), **activity.dict())
    _activity_data.append(new_record)
    _next_id += 1
    return new_record

# Route to get activity data by id
@router.get(
    "/{activity_id}",
    response_model=schemas.ActivityData,
    responses={404: {"model": schemas.ErrorResponse, "description": "Record not found"}},
)
async def get_activity_data(activity_id: int):
    """Get a single activity data record by id."""
    for record in _activity_data:
        if record.id == activity_id:
            return record
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity record not found.")


# Route to list activity data for a patient
@router.get("/", response_model=List[schemas.ActivityData])
async def list_activity_data(patient_id: int, limit: int = 50, offset: int = 0):
    """List activity data for a patient, most recent first."""
    matches = [r for r in _activity_data if r.patient_id == patient_id]
    matches.sort(key=lambda r: r.recorded_at, reverse=True)
    return matches[offset: offset + limit]