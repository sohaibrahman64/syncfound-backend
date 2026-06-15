from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.user_role_model import UserRole
from app.schemas.user_role_schema import UserRoleResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["User Roles"],
)


@router.get("/user-roles", response_model=list[UserRoleResponse])
def get_user_roles(db: Session = Depends(get_db)):
    return db.query(UserRole).order_by(UserRole.id.asc()).all()
