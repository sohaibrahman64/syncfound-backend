from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.employment_type_model import EmploymentType
from app.schemas.employment_type_schema import EmploymentTypeResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Employment Types"],
)


@router.get("/employment-types", response_model=list[EmploymentTypeResponse])
def get_employment_types(db: Session = Depends(get_db)):
    return db.query(EmploymentType).order_by(EmploymentType.id.asc()).all()
