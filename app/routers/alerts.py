# ---------------------------------
# Alerts routes
# ---------------------------------

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import  APIRouter, HTTPException, status, Query, Path
from .. import schemas

router = APIRouter(prefix="/alerts", tags=["Alerts"])

_alerts: List[schemas.Alert] = []
_next_id = 1

# Create alert route
@router.post(   
    "/",
    response_model=schemas.Alert,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)
async def create_alert(alert: schemas.AlertCreate):
    """
    Create an alert. In Phase 4 this is called by the rule engine when a
    reading crosses a threshold, rather than by a client directly.
    """
    global _next_id
    new_alert = schemas.Alert(id=_next_id, triggered_at=datetime.now(timezone.utc), **alert.dict())
    _alerts.append(new_alert)
    _next_id += 1
    return new_alert


# List alerts route
@router.get("/", response_model=List[schemas.Alert])
async def list_alerts(patient_id: Optional[int] = Query (None, description= "ID of the patient whose alerts to retrieve"), status_filter: Optional[str] = Query(None, description="Filter alerts by status")):
    """List alerts, optionally filtered by patient and/or status."""
    results = _alerts
    if patient_id is not None:
        results = [a for a in results if a.patient_id == patient_id]
    if status_filter is not None:
        results = [a for a in results if a.status == status_filter]
    return results

# Get alert by id route
@router.get(
    "/{alert_id}", 
    response_model=schemas.Alert,
    responses={404: {"model": schemas.ErrorResponse, "description": "Alert not found"}},
)
async def get_alert(alert_id: int = Path(..., description="ID of the alert to retrieve")):
    """Get a single alert by id."""
    for a in _alerts:
        if a.id == alert_id:
            return a
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

# Update alert route
@router.patch(
    "/{alert_id}",
    response_model=schemas.Alert,
    responses={404: {"model": schemas.ErrorResponse, "description": "Alert not found"}},
)
async def update_alert(update: schemas.AlertUpdate, alert_id: int = Path(..., description="ID of the alert to update")):
    """Acknowledge or resolve an alert."""
    for i, a in enumerate(_alerts):
        if a.id == alert_id:
            now = datetime.now(timezone.utc)
            updated = a.copy(update={
                "status": update.status,
                "acknowledged_by": update.acknowledged_by if update.acknowledged_by is not None else a.acknowledged_by,
                "acknowledged_at": now if update.status == "acknowledged" else a.acknowledged_at,
                "resolved_at": now if update.status == "resolved" else a.resolved_at,
            })
            _alerts[i] = updated
            return updated
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")