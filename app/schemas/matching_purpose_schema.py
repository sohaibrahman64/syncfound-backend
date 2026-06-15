from pydantic import BaseModel


class MatchingPurposeResponse(BaseModel):
    id: int
    matching_purpose: str
    description: str | None = None
    icon: str | None = None
    selected_icon: str | None = None

    class Config:
        from_attributes = True
