from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.work_authorizations_model import WorkAuthorization
from app.schemas.work_authorization_schema import WorkAuthorizationResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Work Authorizations"]
)


@router.get("/work-authorizations", response_model=List[WorkAuthorizationResponse])
def get_work_authorizations(db: Session = Depends(get_db)):
    work_authorizations = db.query(WorkAuthorization).all()
    return work_authorizations