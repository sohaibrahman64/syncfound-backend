from datetime import datetime

from pydantic import BaseModel


class CofounderSkillResponse(BaseModel):
    id: int
    skill_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True