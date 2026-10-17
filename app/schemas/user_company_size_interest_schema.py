from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class UserCompanySizeInterestBase(BaseModel):
    companySizeId: int = Field(gt=0)

    companyLevelInterestId: int = Field(gt=0)


class UserCompanySizeInterestCreate(UserCompanySizeInterestBase):
    pass


class UserCompanySizeInterestUpdate(UserCompanySizeInterestBase):
    id: int = Field(gt=0)


class UserCompanySizeInterestUpsert(UserCompanySizeInterestBase):
    """
    Used inside PATCH /users/me/profile.

    id == None  -> create
    id != None  -> update
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )


class UserCompanySizeInterestResponse(UserCompanySizeInterestUpsert):
    id: int
    userId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)