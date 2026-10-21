from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProfileEditInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserPromptEdit(ProfileEditInput):
    prompt: int | str
    answer: str


class MatchingGoalEdit(ProfileEditInput):
    answer: int | None = None
    isHiring: bool | str | None = None


class EquitySplitEdit(ProfileEditInput):
    answer: int | None = None
    minEquityRange: int | str | None = None
    maxEquityRange: int | str | None = None


class FounderProfileEdit(ProfileEditInput):
    matchingGoal: MatchingGoalEdit | None = None
    commitmentLevel: int | None = None
    noOfFounders: int | None = Field(default=None, ge=1)
    userSkills: list[int] | None = None
    equitySplit: EquitySplitEdit | None = None


class JobSearchProfileEdit(ProfileEditInput):
    jobSearchAnswer: int | None = None
    jobSearchWorkType: list[int] | None = None
    foundersCanSee: bool | None = None


class BioExperienceEdit(ProfileEditInput):
    title: str | None = None
    primaryRole: int | None = None
    secondaryRole: int | None = None
    yearsOfExperience: int | None = Field(default=None, ge=0)
    bio: str | None = None
    startupIdea: str | None = None
    fundingStage: int | None = None
    riskAppetite: int | None = None
    employmentType: int | None = None
    companyName: str | None = None
    location: str | None = None
    locationType: int | None = None


class CompensationEdit(ProfileEditInput):
    cashEquityExpectation: int | None = None
    expectedMinimumSalary: int | None = None
    salaryDuration: int | None = None
    currency: int | None = None
    amount: Decimal | int | float | str | None = None


class CompanySizeInterestEdit(ProfileEditInput):
    company_size: int
    interest_level: int


class TalentProfileEdit(ProfileEditInput):
    jobSearchProfile: JobSearchProfileEdit | None = None
    bioExperience: BioExperienceEdit | None = None
    compensation: CompensationEdit | None = None
    company_size_interest: list[CompanySizeInterestEdit] | None = None
    workAuthorization: int | None = None


class UserAboutEdit(ProfileEditInput):
    industries: list[int] | None = None
    priorStartupExperience: int | None = None


class LocationPreferenceEdit(ProfileEditInput):
    question_id: int
    selected_answer_id: int


class UserLocationEdit(ProfileEditInput):
    city: int | None = Field(
        default=None,
        validation_alias=AliasChoices("city", "city_id"),
    )
    country: int | None = Field(
        default=None,
        validation_alias=AliasChoices("country", "country_id", "countryId"),
    )
    preference: list[LocationPreferenceEdit] | None = None


class ExperienceEdit(ProfileEditInput):
    title: str | None = None
    company: str | None = None
    currentlyWorkHere: bool | None = None
    startMonth: str | int | None = None
    endMonth: str | int | None = None
    startYear: str | int | None = None
    endYear: str | int | None = None
    description: str | None = None


class EducationEdit(ProfileEditInput):
    school: str | None = None
    degree: str | None = None
    fieldOfStudy: str | None = None
    startMonth: str | int | None = None
    endMonth: str | int | None = None
    startYear: str | int | None = None
    endYear: str | int | None = None
    description: str | None = None


class ExperiencesEdit(ProfileEditInput):
    linkedinJobExperiences: list[ExperienceEdit] | None = None
    additionalJobExperiences: list[ExperienceEdit] | None = None


class EducationCollectionEdit(ProfileEditInput):
    linkedInEducation: list[EducationEdit] | None = None
    additionalEducation: list[EducationEdit] | None = None


class UserProfileDetailsEdit(ProfileEditInput):
    name: str | None = None
    age: int | None = None
    location: UserLocationEdit | None = None
    linkedInUrl: str | None = None
    schedulingLink: str | None = None
    experiences: ExperiencesEdit | None = None
    education: EducationCollectionEdit | None = None


class UserProfileEditRequest(ProfileEditInput):
    headline: str | None = None
    profileImageUri: str | None = None
    userDescribedAs: int | None = Field(
        default=None,
        validation_alias=AliasChoices("userDescribedAs", "user_described_as"),
    )
    userSelectedAs: int | None = Field(
        default=None,
        validation_alias=AliasChoices("userSelectedAs", "user_selected_as"),
    )
    userPrompts: list[UserPromptEdit] | None = None
    # These branches are parsed only after the role selector is known. This lets
    # the endpoint ignore invalid data for the inactive branch on a PATCH.
    userBackgroundAsAFounder: Any = None
    userBackgroundAsATalent: Any = None
    userAbout: UserAboutEdit | None = None
    userProfile: UserProfileDetailsEdit | None = None


class UserProfileEditResponse(BaseModel):
    message: str
    user_id: int
    profile_id: int
