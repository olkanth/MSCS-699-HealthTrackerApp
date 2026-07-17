# -------------------------------------
# Vital Signs routes
# -------------------------------------

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session

from .. import services, models, schemas
from ..auth import ensure_patient_access, get_current_user
from ..database import get_db

router = APIRouter(prefix="/vital-signs", tags=["Vital Signs"])


# Route to create vital sign reading
@router.post(
    "/",
    response_model=schemas.VitalSigns,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Patient not found"},
        422: {"model": schemas.ErrorResponse, "description": "Validation error"},
    },
)
async def create_vital_signs(
    vital_signs: schemas.VitalSignsCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Record a new vital sign reading."""
    ensure_patient_access(db, current_user, vital_signs.patient_id)
    try:
        new_record = services.create_vital_signs(db, vital_signs)
    except services.ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except services.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    services.log_action(db, current_user.id, "create", "vital_signs", new_record.id)
    return new_record


# Get vital sign reading by id
@router.get(
    "/{vital_signs_id}",
    response_model=schemas.VitalSigns,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Reading not found"},
    },
)
async def get_vital_signs(
    vital_signs_id: int = Path(..., description="ID of the vital sign reading to retrieve"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single vital sign reading by id."""
    record = services.get_vital_signs(db, vital_signs_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vital sign reading not found.")
    ensure_patient_access(db, current_user, record.patient_id)
    services.log_action(db, current_user.id, "read", "vital_signs", vital_signs_id)
    return record


# List vital sign readings for a patient
@router.get("/", response_model=List[schemas.VitalSigns])
async def list_vital_signs(
    patient_id: int = Query(..., description="ID of the patient whose vital signs to retrieve"),
    start: Optional[datetime] = Query(None, description="Only include readings recorded at/after this timestamp"),
    end: Optional[datetime] = Query(None, description="Only include readings recorded at/before this timestamp"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip, for pagination"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List vital sign readings for a patient, most recent first. Optionally
    filter to a date range with start/end."""
    ensure_patient_access(db, current_user, patient_id)
    return services.list_vital_signs(db, patient_id, start=start, end=end, limit=limit, offset=offset)
