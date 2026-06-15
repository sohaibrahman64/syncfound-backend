from datetime import datetime

from pydantic import BaseModel


class IndustryResponse(BaseModel):
    id: int
    industry_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True