from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.prior_startup_experience_model import PriorStartupExperience
from app.schemas.prior_startup_experience_schema import PriorStartupExperienceResponse

router = APIRouter(prefix="/api/v1", tags=["Prior Startup Experiences"])


@router.get("/prior-startup-experiences", response_model=List[PriorStartupExperienceResponse])
def get_prior_startup_experiences(db: Session = Depends(get_db)):
    experiences = db.query(PriorStartupExperience).all()
    return experiences