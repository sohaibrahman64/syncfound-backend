from pydantic import BaseModel, Field
from datetime import datetime


class PromptBase(BaseModel):
    prompt_name: str


class PromptCreate(PromptBase):
    pass


class PromptInDBBase(PromptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Prompt(PromptInDBBase):
    pass