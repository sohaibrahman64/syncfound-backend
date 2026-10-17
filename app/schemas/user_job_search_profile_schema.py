from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserJobSearchProfileBase(BaseModel):
    jobSearchProfileId: int = Field(gt=0)


class UserJobSearchProfileCreate(UserJobSearchProfileBase):
    pass


class UserJobSearchProfileUpdate(UserJobSearchProfileBase):
    id: int = Field(gt=0)


class UserJobSearchProfileUpsert(UserJobSearchProfileBase):
    """
    Used inside PATCH /users/me/profile.
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )


class UserJobSearchProfileResponse(UserJobSearchProfileUpsert):
    id: int
    userId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class UserJobSearchProfileWorkTypeBase(BaseModel):
    workTypeId: int = Field(gt=0)


class UserJobSearchProfileWorkTypeCreate(
    UserJobSearchProfileWorkTypeBase
):
    pass


class UserJobSearchProfileWorkTypeUpdate(
    UserJobSearchProfileWorkTypeBase
):
    id: int = Field(gt=0)


class UserJobSearchProfileWorkTypeUpsert(
    UserJobSearchProfileWorkTypeBase
):
    """
    Used inside PATCH /users/me/profile.
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )


class UserJobSearchProfileWorkTypeResponse(
    UserJobSearchProfileWorkTypeUpsert
):
    id: int
    userJobSearchProfileId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)