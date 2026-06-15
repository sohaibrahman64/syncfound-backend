from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.time_commitment_model import TimeCommitment
from app.schemas.time_commitment_schema import TimeCommitmentResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Time Commitments"],
)


@router.get("/time-commitments", response_model=list[TimeCommitmentResponse])
def get_time_commitments(db: Session = Depends(get_db)):
    return db.query(TimeCommitment).order_by(TimeCommitment.id.asc()).all()
