from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.industry_model import Industry
from app.schemas.industry_schema import IndustryResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Industries"],
)


@router.get("/industries", response_model=list[IndustryResponse])
def get_industries(db: Session = Depends(get_db)):
    return db.query(Industry).order_by(Industry.id.asc()).all()