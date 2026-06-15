from datetime import datetime

from pydantic import BaseModel


class CofounderRoleResponse(BaseModel):
    id: int
    role_name: str
    equity_offer: str | None = None
    description: str | None = None
    icon: str | None = None
    selected_icon: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
