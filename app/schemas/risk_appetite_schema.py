from datetime import datetime

from pydantic import BaseModel


class RiskAppetiteResponse(BaseModel):
    id: int
    risk_appetite_name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
