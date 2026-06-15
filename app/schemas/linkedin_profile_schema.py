from pydantic import BaseModel, Field


class LinkedInProfileDatePart(BaseModel):
    year: int | None = None
    month: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileLocation(BaseModel):
    country: str | None = None
    city: str | None = None
    full: str | None = None
    postal_code: str | None = None
    country_code: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileTopEducationSchool(BaseModel):
    name: str | None = None
    urn: str | None = None
    url: str | None = None
    logo_url: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileBasicInfo(BaseModel):
    fullname: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    public_identifier: str
    profile_url: str
    profile_picture_url: str | None = None
    about: str | None = None
    location: LinkedInProfileLocation | None = None
    creator_hashtags: list[str] = Field(default_factory=list)
    is_creator: bool | None = None
    is_influencer: bool | None = None
    is_premium: bool | None = None
    open_to_work: bool | None = None
    created_timestamp: int | None = None
    show_follower_count: bool | None = None
    background_picture_url: str | None = None
    memorialized: bool | None = None
    is_top_voice: bool | None = None
    primary_locale: str | None = None
    urn: str | None = None
    follower_count: int | None = None
    connection_count: int | None = None
    top_education_school: LinkedInProfileTopEducationSchool | None = None
    current_company: str | None = None
    current_company_urn: str | None = None
    top_skills: list[str] = Field(default_factory=list)
    email: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileExperienceItem(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    duration: str | None = None
    start_date: LinkedInProfileDatePart | None = None
    end_date: LinkedInProfileDatePart | None = None
    is_current: bool | None = None
    company_linkedin_url: str | None = None
    company_logo_url: str | None = None
    employment_type: str | None = None
    location_type: str | None = None
    skills: list[str] = Field(default_factory=list)
    company_id: str | None = None
    skills_url: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileEducationItem(BaseModel):
    school: str | None = None
    degree: str | None = None
    degree_name: str | None = None
    field_of_study: str | None = None
    duration: str | None = None
    school_linkedin_url: str | None = None
    start_date: LinkedInProfileDatePart | None = None
    end_date: LinkedInProfileDatePart | None = None

    class Config:
        from_attributes = True


class LinkedInProfileProjectItem(BaseModel):
    name: str | None = None
    description: str | None = None
    is_current: bool | None = None

    class Config:
        from_attributes = True


class LinkedInProfileCertificationItem(BaseModel):
    name: str | None = None
    issuer: str | None = None
    issued_date: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileLanguageItem(BaseModel):
    language: str | None = None
    proficiency: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileCourseItem(BaseModel):
    title: str | None = None

    class Config:
        from_attributes = True


class LinkedInProfileIngestRequest(BaseModel):
    userid: int = Field(gt=0)
    basic_info: LinkedInProfileBasicInfo
    experience: list[LinkedInProfileExperienceItem] = Field(default_factory=list)
    education: list[LinkedInProfileEducationItem] = Field(default_factory=list)
    projects: list[LinkedInProfileProjectItem] = Field(default_factory=list)
    certifications: list[LinkedInProfileCertificationItem] = Field(default_factory=list)
    languages: list[LinkedInProfileLanguageItem] = Field(default_factory=list)
    courses: list[LinkedInProfileCourseItem] = Field(default_factory=list)
    causes: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class LinkedInProfileIngestResponse(BaseModel):
    message: str
    profile_id: int
    user_id: int

    class Config:
        from_attributes = True