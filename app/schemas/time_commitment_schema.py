from datetime import datetime

from pydantic import BaseModel


class TimeCommitmentResponse(BaseModel):
    id: int
    time_commitment_name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
