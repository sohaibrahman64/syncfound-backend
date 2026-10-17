from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserProfileCompensationBase(BaseModel):
    cashEquityExpectationId: int | None = Field(
        default=None,
        gt=0,
    )

    expectedMinimumSalaryId: int | None = Field(
        default=None,
        gt=0,
    )

    salaryDurationId: int | None = Field(
        default=None,
        gt=0,
    )

    currencyId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileCompensationCreate(UserProfileCompensationBase):
    pass


class UserProfileCompensationUpdate(UserProfileCompensationBase):
    id: int = Field(gt=0)


class UserProfileCompensationUpsert(UserProfileCompensationBase):
    """
    Used inside PATCH /users/me/profile.
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileCompensationResponse(UserProfileCompensationUpsert):
    id: int
    userId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)