from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict

class UserProfileExperienceBase(BaseModel):
    """
    Editable work-experience information belonging to a SyncFound user profile.

    This is intentionally separate from LinkedInProfileExperience.
    LinkedIn data is imported/source data; this schema represents the
    editable SyncFound profile copy.
    """
    title: str | None = Field(default=None, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    description: str | None = None

    startDate: date | None = None
    endDate: date | None = None

    currentlyWorkHere: bool = False

    employmentType: int | None = Field(default=None, gt=0)
    locationType: int | None = Field(default=None, gt=0)

class UserProfileExperienceCreate(UserProfileExperienceBase):
    """
    Used when the frontend creates a new editable experience.
    """

    sourceLinkedInExperienceId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileExperienceUpdate(UserProfileExperienceBase):
    """
    Used when the frontend updates an existing editable experience.
    """

    id: int = Field(gt=0)

    sourceLinkedInExperienceId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileExperienceUpsert(UserProfileExperienceBase):
    """
    Used inside PATCH /users/me/profile.

    id == None  -> create
    id != None  -> update
    """

    id: int | None = Field(
        default=None,
        gt=0,
    )

    sourceLinkedInExperienceId: int | None = Field(
        default=None,
        gt=0,
    )


class UserProfileExperienceResponse(UserProfileExperienceUpsert):
    """
    API representation returned to the mobile application.
    """

    id: int
    userProfileId: int

    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)