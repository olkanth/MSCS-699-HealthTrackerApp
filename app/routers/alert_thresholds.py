# -----------------------------------
# Alert thresholds routes
# ------------------------------------ 

from datetime import datetime, timezone
from typing import List
from fastapi import  APIRouter, HTTPException, status, Query, Path
from .. import schemas

router = APIRouter(prefix="/alert-thresholds", tags=["Alerts"])

# In-memory store, skeleton/demo only -- not persisted
# replaced by SQLAlchemy with PostgreSQL in Phase 3.
_thresholds: List[schemas.AlertThreshold] = []
_next_id = 1

# Route to create alert threshold
@router.post(
    "/",
    response_model=schemas.AlertThreshold,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)
async def create_alert_threshold(threshold: schemas.AlertThresholdCreate):
    """Set a threshold for one metric (e.g. heart_rate) for a patient."""
    global _next_id
    new_threshold = schemas.AlertThreshold(id=_next_id, updated_at=datetime.now(timezone.utc), **threshold.dict())
    _thresholds.append(new_threshold)
    _next_id += 1
    return new_threshold


# Route to list alert thresholds
@router.get("/", response_model=List[schemas.AlertThreshold])
async def list_alert_thresholds(patient_id: int = Query(..., description="ID of the patient whose alert thresholds to retrieve")) :
    """List all configured thresholds for a patient."""
    return [t for t in _thresholds if t.patient_id == patient_id]
    

# Route to update alert threshold
@router.put(
    "/{threshold_id}",
    response_model=schemas.AlertThreshold,
    responses={404: {"model": schemas.ErrorResponse, "description": "Threshold not found"}},
)
async def update_alert_threshold(threshold: schemas.AlertThresholdCreate, threshold_id: int = Path(..., ge=1, description="ID of the alert threshold to update")):
    """Update an existing threshold."""
    for i, t in enumerate(_thresholds):
        if t.id == threshold_id:
            updated = schemas.AlertThreshold(id=threshold_id, updated_at=datetime.now(timezone.utc), **threshold.dict())
            _thresholds[i] = updated
            return updated
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threshold not found.")


# Route to delete alert threshold
@router.delete(
    "/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": schemas.ErrorResponse, "description": "Threshold not found"}},
)
async def delete_alert_threshold(threshold_id: int = Path(..., ge=1, description="ID of the alert threshold to delete")):
    """Remove a threshold."""
    for i, t in enumerate(_thresholds):
        if t.id == threshold_id:
            _thresholds.pop(i)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Threshold not found.")
