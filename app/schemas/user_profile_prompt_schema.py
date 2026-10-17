from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserProfilePromptBase(BaseModel):
    promptId: int = Field(gt=0)

    answer: str = Field(
        min_length=1,
        max_length=2000,
    )

    displayOrder: int | None = Field(
        default=None,
        ge=0,
    )


class UserProfilePromptCreate(UserProfilePromptBase):
    pass


class UserProfilePromptUpdate(UserProfilePromptBase):
    id: int = Field(gt=0)


class UserProfilePromptUpsert(UserProfilePromptBase):
    """
    Used inside PATCH /users/me/profile.

    id == None  -> create
    id != None  -> update
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfilePromptResponse(UserProfilePromptUpsert):
    id: int
    userProfileId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)