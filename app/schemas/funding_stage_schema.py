from datetime import datetime

from pydantic import BaseModel


class FundingStageResponse(BaseModel):
    id: int
    funding_stage_name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
