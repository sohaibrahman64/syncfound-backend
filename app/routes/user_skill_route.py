from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.user_skill_model import UserSkill
from app.schemas.user_skill_schema import UserSkillResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["User Skills"],
)


@router.get("/user-skills", response_model=list[UserSkillResponse])
def get_user_skills(db: Session = Depends(get_db)):
    return db.query(UserSkill).order_by(UserSkill.id.asc()).all()