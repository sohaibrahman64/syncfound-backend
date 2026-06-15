from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.cofounder_role_model import CofounderRole
from app.schemas.cofounder_role_schema import CofounderRoleResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Cofounder Roles"],
)


@router.get("/cofounder-roles", response_model=list[CofounderRoleResponse])
def get_cofounder_roles(db: Session = Depends(get_db)):
    return db.query(CofounderRole).order_by(CofounderRole.id.asc()).all()
