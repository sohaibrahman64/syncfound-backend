from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CompanySizeInterestLevelBase(BaseModel):
    company_size_interest_level: str

class CompanySizeInterestLevelCreate(CompanySizeInterestLevelBase):
    pass

class CompanySizeInterestLevelResponse(CompanySizeInterestLevelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True