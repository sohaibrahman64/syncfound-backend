from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InviteProfileCard(BaseModel):
    user_id: int
    display_name: str | None = None
    profile_photo_url: str | None = None
    location_text: str | None = None
    intent_badge: str | None = None
    time_commitment: str | None = None
    role_tags: list[str] = Field(default_factory=list)


class InviteItem(BaseModel):
    invite_id: str
    status: str
    message: str | None = None
    created_at: datetime
    updated_at: datetime
    read_at: datetime | None = None
    responded_at: datetime | None = None


class InviteLinkedInExperienceResponse(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    description: str | None = None
    duration: str | None = None
    start_year: int | None = None
    start_month: str | None = None
    end_year: int | None = None
    end_month: str | None = None
    is_current: bool | None = None
    company_linkedin_url: str | None = None
    company_logo_url: str | None = None
    employment_type: str | None = None
    location_type: str | None = None


class InviteEducationResponse(BaseModel):
    school: str | None = None
    degree: str | None = None
    degree_name: str | None = None
    field_of_study: str | None = None
    duration: str | None = None
    school_linkedin_url: str | None = None
    start_year: int | None = None
    start_month: str | None = None
    end_year: int | None = None
    end_month: str | None = None


class InviteUserDetailsResponse(BaseModel):
    user_id: int
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    age: int | None = None
    title: str | None = None
    profile_photo_url: str | None = None
    country_code: str | None = None
    city: str | None = None
    location_text: str | None = None
    user_role: str | None = None
    role: str | None = None
    intent_badge: str | None = None
    bio: str | None = None
    experience_summary: str | None = None
    startup_idea: str | None = None
    linkedin_url: str | None = None
    user_skills: list[str] = Field(default_factory=list)
    cofounder_skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    linkedin_headline: str | None = None
    linkedin_current_company: str | None = None
    linkedin_location: str | None = None
    linkedin_top_education_school_name: str | None = None
    linkedin_experiences: list[InviteLinkedInExperienceResponse] = Field(default_factory=list)
    education_details: list[InviteEducationResponse] = Field(default_factory=list)


class ReceivedInviteEntry(BaseModel):
    invite: InviteItem
    performed_by_profile: InviteProfileCard
    from_profile: InviteProfileCard
    source_profile_details: InviteUserDetailsResponse | None = None


class ReceivedInviteListResponse(BaseModel):
    items: list[ReceivedInviteEntry]
    next_cursor: str | None = None
    has_more: bool


class SentInviteEntry(BaseModel):
    invite: InviteItem
    performed_by_profile: InviteProfileCard
    to_profile: InviteProfileCard
    target_profile_details: InviteUserDetailsResponse | None = None


class SentInviteListResponse(BaseModel):
    items: list[SentInviteEntry]
    next_cursor: str | None = None
    has_more: bool


class SavedEntry(BaseModel):
    saved_id: int
    saved_at: datetime
    performed_by_profile: InviteProfileCard
    profile: InviteProfileCard
    target_profile_details: InviteUserDetailsResponse | None = None


class SavedListResponse(BaseModel):
    items: list[SavedEntry]
    next_cursor: str | None = None
    has_more: bool


class PassedEntry(BaseModel):
    passed_id: int
    passed_at: datetime
    performed_by_profile: InviteProfileCard
    profile: InviteProfileCard
    target_profile_details: InviteUserDetailsResponse | None = None


class PassedListResponse(BaseModel):
    items: list[PassedEntry]
    next_cursor: str | None = None
    has_more: bool


class InviteCountsResponse(BaseModel):
    invites_pending: int
    invites_unread: int
    sent_pending: int
    saved_total: int
    passed_total: int


VALID_MUTATE_ACTIONS = {"accept", "decline", "mark_read"}


class InviteMutateRequest(BaseModel):
    action: str = Field(..., description="accept | decline | mark_read")
    request_id: UUID | None = None


class InviteMutateResponse(BaseModel):
    invite_id: str
    status: str
    updated_at: datetime
    mutual_match: bool = False
    match_id: int | None = None


class InviteWithdrawRequest(BaseModel):
    request_id: UUID | None = None


class InviteWithdrawResponse(BaseModel):
    invite_id: str
    status: str
    updated_at: datetime
