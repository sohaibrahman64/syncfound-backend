from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.primary_role_model import PrimaryRole
from app.schemas.primary_role_schema import PrimaryRoleResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Primary Roles"],
)


@router.get("/primary-roles", response_model=list[PrimaryRoleResponse])
def get_primary_roles(db: Session = Depends(get_db)):
    return db.query(PrimaryRole).order_by(PrimaryRole.id.asc()).all()