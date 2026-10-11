from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WorkAuthorizationBase(BaseModel):
    work_authorization: str


class WorkAuthorizationCreate(WorkAuthorizationBase):
    pass


class WorkAuthorizationUpdate(BaseModel):
    work_authorization: Optional[str] = None


class WorkAuthorizationResponse(WorkAuthorizationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True