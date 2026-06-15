from datetime import datetime

from pydantic import BaseModel


class LocationTypeResponse(BaseModel):
    id: int
    location_type_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
