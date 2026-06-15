from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.location_type_model import LocationType
from app.schemas.location_type_schema import LocationTypeResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Location Types"],
)


@router.get("/location-types", response_model=list[LocationTypeResponse])
def get_location_types(db: Session = Depends(get_db)):
    return db.query(LocationType).order_by(LocationType.id.asc()).all()
