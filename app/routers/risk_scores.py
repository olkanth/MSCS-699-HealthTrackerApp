# ----------------------------------
# Risk Score routes
# ------------------------------------ 
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status, Query, Path
from .. import schemas

router = APIRouter(prefix="/risk-scores", tags=["RiskScores"])

_risk_scores: List[schemas.RiskScore] = []
_next_id = 1

# Route to create risk score
@router.post(
    "/",
    response_model=schemas.RiskScore,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": schemas.ErrorResponse, "description": "Validation error"}},
)
async def create_risk_score(risk_score: schemas.RiskScoreCreate):
    """
    Store a newly calculated risk score. In Phase 5 this is called by the
    scoring model rather than by a client directly.
    """
    global _next_id
    new_score = schemas.RiskScore(id=_next_id, calculated_at=datetime.now(timezone.utc), **risk_score.dict())
    _risk_scores.append(new_score)
    _next_id += 1
    return new_score


# Route to get list of risk scores
@router.get("/", response_model=List[schemas.RiskScore])
async def list_risk_scores(patient_id: int = Query(..., description="ID of the patient whose risk score to retrieve"), history: bool = Query(False, description="Whether to retrieve the full risk score history for the patient")):
    """
    Get risk score(s) for a patient. By default returns just the most
    recent score; pass history=true for the full trend.
    """
    matches = [r for r in _risk_scores if r.patient_id == patient_id]
    matches.sort(key=lambda r: r.calculated_at, reverse=True)
    if history:
        return matches
    return matches[:1]


# Route to get risk score by id
@router.get(
    "/{risk_score_id}",
    response_model=schemas.RiskScore,
    responses={404: {"model": schemas.ErrorResponse, "description": "Risk score not found"}},
)
async def get_risk_score(risk_score_id: int = Path(..., description="ID of the risk score to retrieve")):
    """Get a single risk score record by id."""
    for r in _risk_scores:
        if r.id == risk_score_id:
            return r
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk score not found.")
