from datetime import date, datetime

from pydantic import BaseModel, Field, ConfigDict


class UserProfileEducationBase(BaseModel):
    """
    Editable education information belonging to a SyncFound profile.
    """

    school: str | None = Field(
        default=None,
        max_length=255,
    )

    degree: str | None = Field(
        default=None,
        max_length=255,
    )

    degreeName: str | None = Field(
        default=None,
        max_length=255,
    )

    fieldOfStudy: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    startDate: date | None = None
    endDate: date | None = None


class UserProfileEducationCreate(UserProfileEducationBase):
    """
    Used when creating a new editable education record.
    """

    sourceLinkedInEducationId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileEducationUpdate(UserProfileEducationBase):
    """
    Used when updating an existing education record.
    """

    id: int = Field(gt=0)

    sourceLinkedInEducationId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileEducationUpsert(UserProfileEducationBase):
    """
    Used inside PATCH /users/me/profile.

    id == None  -> create
    id != None  -> update
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )

    sourceLinkedInEducationId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileEducationResponse(UserProfileEducationUpsert):
    """
    API representation returned to the mobile application.
    """

    id: int
    userProfileId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)