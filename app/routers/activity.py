# ----------------------------------
# Activity routers
# ------------------------------------

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from .. import services, models, schemas
from ..auth import ensure_patient_access, get_current_user
from ..database import get_db

router = APIRouter(prefix="/activity-data", tags=["Activity"])


# Route to create activity data
@router.post(
    "/",
    response_model=schemas.ActivityData,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Patient not found"},
        422: {"model": schemas.ErrorResponse, "description": "Validation error"},
    },
)
async def create_activity_data(
    activity: schemas.ActivityDataCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Record new activity data (steps, active minutes) for a patient."""
    ensure_patient_access(db, current_user, activity.patient_id)
    try:
        new_record = services.create_activity_data(db, activity)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    services.log_action(db, current_user.id, "create", "activity_data", new_record.id)
    return new_record


# Route to get activity data by id
@router.get(
    "/{activity_id}",
    response_model=schemas.ActivityData,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Record not found"},
    },
)
async def get_activity_data(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single activity data record by id."""
    record = services.get_activity_data(db, activity_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity record not found.")
    ensure_patient_access(db, current_user, record.patient_id)
    services.log_action(db, current_user.id, "read", "activity_data", activity_id)
    return record


# Route to list activity data for a patient
@router.get("/", response_model=List[schemas.ActivityData])
async def list_activity_data(
    patient_id: int,
    start: Optional[datetime] = Query(None, description="Only include records at/after this timestamp"),
    end: Optional[datetime] = Query(None, description="Only include records at/before this timestamp"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List activity data for a patient, most recent first. Optionally
    filter to a date range with start/end."""
    ensure_patient_access(db, current_user, patient_id)
    return services.list_activity_data(db, patient_id, start=start, end=end, limit=limit, offset=offset)
