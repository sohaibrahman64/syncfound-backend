from datetime import datetime
from pydantic import BaseModel


class PriorStartupExperienceResponse(BaseModel):
    id: int
    prior_startup_experience: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True