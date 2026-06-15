from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.secondary_role_model import SecondaryRole
from app.schemas.secondary_role_schema import SecondaryRoleResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Secondary Roles"],
)


@router.get("/secondary-roles", response_model=list[SecondaryRoleResponse])
def get_secondary_roles(db: Session = Depends(get_db)):
    return db.query(SecondaryRole).order_by(SecondaryRole.id.asc()).all()