from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.company_size_interest_level_model import CompanySizeInterestLevel
from app.schemas.company_size_interest_level_schema import CompanySizeInterestLevelResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Company Size Interest Level"]
)


@router.get("/company-size-interest-levels", response_model=list[CompanySizeInterestLevelResponse])
def get_company_size_interest_levels(db: Session = Depends(get_db)):
    return db.query(CompanySizeInterestLevel).order_by(CompanySizeInterestLevel.id.asc()).all()