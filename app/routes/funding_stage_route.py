from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.funding_stage_model import FundingStage
from app.schemas.funding_stage_schema import FundingStageResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Funding Stages"],
)


@router.get("/funding-stages", response_model=list[FundingStageResponse])
def get_funding_stages(db: Session = Depends(get_db)):
    return db.query(FundingStage).order_by(FundingStage.id.asc()).all()
