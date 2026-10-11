from pydantic import BaseModel
from datetime import datetime


class CommitmentLevelResponse(BaseModel):
    id: int
    commitment_level: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True