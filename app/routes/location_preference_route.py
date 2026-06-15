from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.location_preference_model import LocationPreferenceQuestion
from app.schemas.location_preference_schema import LocationPreferenceQuestionResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Location Preference"],
)


@router.get("/location-preference", response_model=list[LocationPreferenceQuestionResponse])
def get_location_preference(db: Session = Depends(get_db)):
    return db.query(LocationPreferenceQuestion).order_by(LocationPreferenceQuestion.id.asc()).all()
