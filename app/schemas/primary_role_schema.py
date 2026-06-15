from datetime import datetime

from pydantic import BaseModel


class PrimaryRoleResponse(BaseModel):
    id: int
    primary_role_name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True