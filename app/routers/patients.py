from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status

from .. import schemas


router = APIRouter(prefix="/patients", tags=["Patients"])
