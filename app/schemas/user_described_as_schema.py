from datetime import datetime
from pydantic import BaseModel


class UserDescribedAsResponse(BaseModel):
    id: int
    described_as: str
    icon: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True