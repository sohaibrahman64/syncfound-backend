from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class LocationPreferenceSelection(BaseModel):
    question_id: int = Field(gt=0)
    selected_answer_id: int = Field(gt=0)


class LinkedInProfilePreview(BaseModel):
    headline: str | None = None
    firstOrganization: str | None = None
    firstEducationInstitution: str | None = None
    firstLocation: str | None = None
    connections: str | None = None


class ProfileImageCropRect(BaseModel):
    x: float
    y: float
    width: float
    height: float


class UserProfileUpsertRequest(BaseModel):
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    dateOfBirth: date
    age: int | None = Field(default=None, ge=0)
    state: int = Field(gt=0)
    city: int = Field(gt=0)

    locationPreference: list[LocationPreferenceSelection] = Field(default_factory=list)

    matchingPurpose: int = Field(gt=0)
    userRole: int = Field(gt=0)
    cofounderRole: int = Field(gt=0)

    userSkills: list[int] = Field(default_factory=list)
    cofounderSkills: list[int] = Field(default_factory=list)
    industries: list[int] = Field(default_factory=list)

    title: str | None = None
    primaryRole: int = Field(gt=0)
    secondaryRole: int | None = Field(default=None, gt=0)

    bio: str | None = None
    startupIdea: str | None = None

    fundingStage: int = Field(gt=0)
    timeCommitment: int = Field(gt=0)
    riskAppetite: int = Field(gt=0)
    employmentType: int = Field(gt=0)

    companyName: str | None = None
    experienceLocation: str | None = None
    locationType: int | None = Field(default=None, gt=0)

    startDate: datetime | None = None
    currentlyWorkHere: bool = False
    endDate: datetime | None = None

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def empty_string_dates_to_none(cls, value):
        if value == "":
            return None
        return value

    @model_validator(mode="after")
    def normalize_employment_dates(self):
        if self.currentlyWorkHere:
            self.endDate = None
        return self

    linkedinUrl: str | None = None
    linkedinUsername: str | None = None
    linkedinProfilePreview: LinkedInProfilePreview | None = None
    linkedinProfilePictureUrl: str | None = None

    pendingProfileImageUri: str | None = None
    pendingProfileImageSource: str | None = None

    profileImageRotation: float = 0
    profileImageScale: float = 1
    profileImageTranslateX: float = 0
    profileImageTranslateY: float = 0
    profileImageCropRect: ProfileImageCropRect | None = None

    profileImageUri: str | None = None
    profileImageSource: str | None = None


class UserProfileUpsertResponse(BaseModel):
    message: str
    user_id: int
    profile_id: int