from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.user_company_size_interest_schema import (
    UserCompanySizeInterestUpsert,
    UserCompanySizeInterestResponse,
)

from app.schemas.user_job_search_profile_schema import (
    UserJobSearchProfileUpsert,
    UserJobSearchProfileResponse,
    UserJobSearchProfileWorkTypeUpsert,
    UserJobSearchProfileWorkTypeResponse,
)

from app.schemas.user_profile_compensation_schema import (
    UserProfileCompensationUpsert,
    UserProfileCompensationResponse,
)

from app.schemas.user_profile_education_schema import (
    UserProfileEducationUpsert,
    UserProfileEducationResponse,
)

from app.schemas.user_profile_experience_schema import (
    UserProfileExperienceUpsert,
    UserProfileExperienceResponse,
)

from app.schemas.user_profile_prompt_schema import (
    UserProfilePromptUpsert,
    UserProfilePromptResponse,
)


class LocationPreferenceSelection(BaseModel):
    question_id: int = Field(gt=0)
    selected_answer_id: int = Field(gt=0)


class LocationPreferenceAnswerResponse(BaseModel):
    id: int
    answer: str


class LocationPreferenceQuestionResponse(BaseModel):
    question_id: int
    question: str
    answers: list[LocationPreferenceAnswerResponse]


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
    # ---------------------------------------------------------
    # Basic profile
    # ---------------------------------------------------------

    firstName: str = Field(
        min_length=1,
        max_length=100,
    )

    lastName: str = Field(
        min_length=1,
        max_length=100,
    )

    dateOfBirth: date

    age: int | None = Field(
        default=None,
        ge=0,
    )

    headline: str | None = Field(
        default=None,
        max_length=500,
    )

    founderCount: int | None = Field(
        default=None,
        ge=0,
    )

    priorStartupExperienceId: int | None = Field(
        default=None,
        gt=0,
    )

    workAuthorizationId: int | None = Field(
        default=None,
        gt=0,
    )

    state: int = Field(gt=0)

    city: int = Field(gt=0)

    # ---------------------------------------------------------
    # Location preferences
    # ---------------------------------------------------------

    locationPreference: list[LocationPreferenceSelection] = Field(
        default_factory=list
    )

    # IMPORTANT:
    # locationPreferenceQuestions is intentionally NOT part
    # of the request. It is lookup/display data returned by GET.

    # ---------------------------------------------------------
    # Matching / roles
    # ---------------------------------------------------------

    matchingPurpose: int = Field(gt=0)

    userRole: int = Field(gt=0)

    cofounderRole: int = Field(gt=0)

    userSkills: list[int] = Field(
        default_factory=list
    )

    cofounderSkills: list[int] = Field(
        default_factory=list
    )

    industries: list[int] = Field(
        default_factory=list
    )

    title: str | None = Field(
        default=None,
        max_length=255,
    )

    primaryRole: int = Field(gt=0)

    secondaryRole: int | None = Field(
        default=None,
        gt=0,
    )

    # ---------------------------------------------------------
    # Profile description
    # ---------------------------------------------------------

    bio: str | None = None

    startupIdea: str | None = None

    # ---------------------------------------------------------
    # Current employment / experience summary
    # ---------------------------------------------------------

    fundingStage: int = Field(gt=0)

    timeCommitment: int = Field(gt=0)

    riskAppetite: int = Field(gt=0)

    employmentType: int = Field(gt=0)

    companyName: str | None = Field(
        default=None,
        max_length=255,
    )

    experienceLocation: str | None = Field(
        default=None,
        max_length=255,
    )

    locationType: int | None = Field(
        default=None,
        gt=0,
    )

    startDate: datetime | None = None

    currentlyWorkHere: bool = False

    endDate: datetime | None = None

    @field_validator(
        "startDate",
        "endDate",
        mode="before",
    )
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

    # ---------------------------------------------------------
    # Editable experiences
    # ---------------------------------------------------------

    experiences: list[
        UserProfileExperienceUpsert
    ] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Editable education
    # ---------------------------------------------------------

    education: list[
        UserProfileEducationUpsert
    ] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Company size interest
    # ---------------------------------------------------------

    companySizeInterests: list[
        UserCompanySizeInterestUpsert
    ] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Compensation
    # ---------------------------------------------------------

    compensation: UserProfileCompensationUpsert | None = None

    # ---------------------------------------------------------
    # Job search
    # ---------------------------------------------------------

    jobSearchProfile: UserJobSearchProfileUpsert | None = None

    jobSearchProfileWorkTypes: list[
        UserJobSearchProfileWorkTypeUpsert
    ] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Profile prompts
    # ---------------------------------------------------------

    prompts: list[
        UserProfilePromptUpsert
    ] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # LinkedIn
    # ---------------------------------------------------------

    linkedinUrl: str | None = None

    linkedinUsername: str | None = None

    linkedinProfilePreview: LinkedInProfilePreview | None = None

    linkedinProfilePictureUrl: str | None = None

    # ---------------------------------------------------------
    # Profile image
    # ---------------------------------------------------------

    pendingProfileImageUri: str | None = None

    pendingProfileImageSource: str | None = None

    profileImageRotation: float = 0

    profileImageScale: float = 1

    profileImageTranslateX: float = 0

    profileImageTranslateY: float = 0

    profileImageCropRect: ProfileImageCropRect | None = None

    profileImageUri: str | None = None

    profileImageSource: str | None = None


class LocationDetailsResponse(BaseModel):
    country_id: int | None = None
    country_name: str | None = None
    selected_state: str | None = None
    selected_city: str | None = None

    states: list[str] = Field(
        default_factory=list
    )

    cities: list[str] = Field(
        default_factory=list
    )


class UserProfileResponse(UserProfileUpsertRequest):
    userId: int
    profileId: int

    locationDetails: LocationDetailsResponse | None = None

    locationPreferenceQuestions: list[
        LocationPreferenceQuestionResponse
    ] = Field(
        default_factory=list
    )

    # These are response representations.
    # They are optional initially so GET can still work while
    # the corresponding persistence implementation is completed.

    experienceDetails: list[
        UserProfileExperienceResponse
    ] = Field(
        default_factory=list
    )

    educationDetails: list[
        UserProfileEducationResponse
    ] = Field(
        default_factory=list
    )

    companySizeInterestDetails: list[
        UserCompanySizeInterestResponse
    ] = Field(
        default_factory=list
    )

    compensationDetails: UserProfileCompensationResponse | None = None

    jobSearchProfileDetails: UserJobSearchProfileResponse | None = None

    jobSearchProfileWorkTypeDetails: list[
        UserJobSearchProfileWorkTypeResponse
    ] = Field(
        default_factory=list
    )

    promptDetails: list[
        UserProfilePromptResponse
    ] = Field(
        default_factory=list
    )


class UserProfileUpsertResponse(BaseModel):
    message: str
    user_id: int
    profile_id: int