from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # type: ignore

from app.database import get_db
from app.models.cofounder_skill_model import CofounderSkill
from app.schemas.cofounder_skill_schema import CofounderSkillResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Cofounder Skills"],
)


@router.get("/cofounder-skills", response_model=list[CofounderSkillResponse])
def get_cofounder_skills(db: Session = Depends(get_db)):
    return db.query(CofounderSkill).order_by(CofounderSkill.id.asc()).all()