from pydantic import BaseModel
from datetime import datetime


class EquitySplitResponse(BaseModel):
    id: int
    equity_split: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True