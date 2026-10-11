from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MatchingGoalResponse(BaseModel):
    id: int
    matching_goal: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True