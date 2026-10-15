from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.user_described_as_model import UserDescribedAs
from app.schemas.user_described_as_schema import UserDescribedAsResponse

router = APIRouter(prefix="/api/v1", tags=["User Described As"])


@router.get("/user-described-as", response_model=List[UserDescribedAsResponse])
def get_user_described_as(db: Session = Depends(get_db)):
    records = db.query(UserDescribedAs).all()
    return records