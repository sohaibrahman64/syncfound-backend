from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.risk_appetite_model import RiskAppetite
from app.schemas.risk_appetite_schema import RiskAppetiteResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Risk Appetites"],
)


@router.get("/risk-appetites", response_model=list[RiskAppetiteResponse])
def get_risk_appetites(db: Session = Depends(get_db)):
    return db.query(RiskAppetite).order_by(RiskAppetite.id.asc()).all()
