from datetime import datetime

from pydantic import BaseModel


class SecondaryRoleResponse(BaseModel):
    id: int
    secondary_role_name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True