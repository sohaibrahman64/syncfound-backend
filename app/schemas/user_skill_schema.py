from datetime import datetime

from pydantic import BaseModel


class UserSkillResponse(BaseModel):
    id: int
    skill_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True