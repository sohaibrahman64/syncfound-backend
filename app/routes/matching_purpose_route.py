from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.matching_purpose_model import MatchingPurpose
from app.schemas.matching_purpose_schema import MatchingPurposeResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Matching Purpose"],
)


@router.get("/matching-purpose", response_model=list[MatchingPurposeResponse])
def get_matching_purpose(db: Session = Depends(get_db)):
    return db.query(MatchingPurpose).order_by(MatchingPurpose.id.asc()).all()
