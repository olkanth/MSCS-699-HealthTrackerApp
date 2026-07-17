# --------------------------------------
# Patient routes
# --------------------------------------
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session

from .. import services, models, schemas
from ..auth import ensure_patient_access, get_current_user, require_role
from ..database import get_db


router = APIRouter(prefix="/patients", tags=["Patients"])


# Route to create new patient
@router.post(
    "/",
    response_model=schemas.Patient,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "it_staff cannot create patient profiles"},
        409: {"model": schemas.ErrorResponse, "description": "MRN already in use"},
        422: {"model": schemas.ErrorResponse, "description": "Validation error"},
    },
)
async def create_patient(
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new patient profile. Patients are always linked to their own
    account; provider/admin callers must supply user_id for the account
    being onboarded."""
    if current_user.role == "it_staff":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="it_staff cannot create patient profiles.")

    if current_user.role == "patient":
        target_user_id = current_user.id
    else:
        if patient.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="user_id is required when a provider/admin creates a patient profile.",
            )
        target_user_id = patient.user_id

    try:
        new_patient = services.create_patient(db, patient, target_user_id)
    except services.DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    services.log_action(db, current_user.id, "create", "patients", new_patient.id)
    return new_patient


# Route to get list of patients
@router.get("/", response_model=List[schemas.Patient])
async def list_patients(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    # require_role(...) IS the role check here -- see delete_patient below.
    current_user: models.User = Depends(require_role("provider", "admin")),
):
    """List patients, with basic pagination. Provider/admin only."""
    return services.list_patients(db, limit=limit, offset=offset)


# Route to get patient by id
@router.get(
    "/{patient_id}",
    response_model=schemas.Patient,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Patient not found"},
    },
)
async def get_patient(
    patient_id: int = Path(..., description="ID of the patient to retrieve"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single patient's profile by id."""
    ensure_patient_access(db, current_user, patient_id)
    patient = services.get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    services.log_action(db, current_user.id, "read", "patients", patient_id)
    return patient


# Route to update patient
@router.put(
    "/{patient_id}",
    response_model=schemas.Patient,
    responses={
        403: {"model": schemas.ErrorResponse, "description": "Not authorized for this patient"},
        404: {"model": schemas.ErrorResponse, "description": "Patient not found"},
        409: {"model": schemas.ErrorResponse, "description": "MRN already in use"},
    },
)
async def update_patient(
    patient: schemas.PatientCreate,
    patient_id: int = Path(..., description="ID of the patient to update"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update a patient's profile."""
    ensure_patient_access(db, current_user, patient_id)
    try:
        updated = services.update_patient(db, patient_id, patient)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except services.DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    services.log_action(db, current_user.id, "update", "patients", patient_id)
    return updated


# Route to delete patient
@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": schemas.ErrorResponse, "description": "Patient not found"}},
)
async def delete_patient(
    patient_id: int = Path(..., description="ID of the patient to delete"),
    db: Session = Depends(get_db),
    # require_role(...) IS the role check here -- it runs before the function
    # body and raises 403 itself for any role other than provider/admin.
    current_user: models.User = Depends(require_role("provider", "admin")),
):
    """Delete a patient profile. Provider/admin only -- not self-service."""
    try:
        services.delete_patient(db, patient_id)
    except services.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    services.log_action(db, current_user.id, "delete", "patients", patient_id)
