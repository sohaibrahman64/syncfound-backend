from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.equity_split_model import EquitySplit
from app.schemas.equity_split_schema import EquitySplitResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Equity Split Levels"]
)


@router.get("/equity-split", response_model=List[EquitySplitResponse])
def get_equity_split(db: Session = Depends(get_db)):
    equity_split = db.query(EquitySplit).order_by(EquitySplit.equity_split.asc()).all()
    return equity_split