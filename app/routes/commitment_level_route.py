from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.commitment_level_model import CommitmentLevel
from app.schemas.commitment_level_schema import CommitmentLevelResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Commitment Levels"]
)


@router.get("/commitment-levels", response_model=List[CommitmentLevelResponse])
def get_commitment_levels(db: Session = Depends(get_db)):
    commitment_levels = db.query(CommitmentLevel).order_by(CommitmentLevel.commitment_level.asc()).all()
    return commitment_levels