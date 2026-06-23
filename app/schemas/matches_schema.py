from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MatchFeedMode(str, Enum):
    discover = "discover"
    matchmaking = "matchmaking"


class MatchActionType(str, Enum):
    like = "like"
    pass_action = "pass"
    save = "save"
    unsave = "unsave"


class MatchItemResponse(BaseModel):
    candidate_id: int
    display_name: str | None = None
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
    user_skills: list[str] = Field(default_factory=list)
    cofounder_skills: list[str] = Field(default_factory=list)
    linkedin_headline: str | None = None
    linkedin_current_company: str | None = None
    linkedin_location: str | None = None
    linkedin_top_education_school_name: str | None = None
    linkedin_experiences: list[LinkedInExperienceResponse] = Field(default_factory=list)
    match_score: float
    match_reasons: list[str] = Field(default_factory=list)
    liked: bool = False
    passed: bool = False
    saved: bool = False


class MatchesFeedResponse(BaseModel):
    items: list[MatchItemResponse]
    next_cursor: str | None = None


class MatchActionRequest(BaseModel):
    action: MatchActionType
    connection_message: str | None = Field(default=None, max_length=1000)
    request_id: UUID | None = None


class MatchActionResponse(BaseModel):
    action: str
    mutual_match: bool = False
    connection_message_saved: bool = False
    swipe_allowed: bool = True
    paywall_required: bool = False
    ad_due_now: bool = False
    plan_tier: str | None = None
    swipes_used: int | None = None
    swipes_remaining: int | None = None


class LinkedInExperienceResponse(BaseModel):
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


class MatchSummaryResponse(BaseModel):
    discover_count: int
    matchmaking_count: int
    unseen_count: int


class PublicProfileResponse(BaseModel):
    candidate_id: int
    display_name: str | None = None
    profile_photo_url: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    bio: str | None = None
    startup_idea: str | None = None
    country_code: str | None = None
    city: str | None = None
    location_text: str | None = None
    role: str | None = None
    intent_badge: str | None = None
    linkedin_url: str | None = None
    user_skills: list[str] = Field(default_factory=list)
    cofounder_skills: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)


class MatchRow(BaseModel):
    candidate_id: int
    profile_id: int
    display_name: str | None = None
    profile_photo_url: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    city: str | None = None
    country_code: str | None = None
    location_text: str | None = None
    role: str | None = None
    user_role: str | None = None
    intent_badge: str | None = None
    experience_summary: str | None = None
    primary_role_id: int | None = None
    cofounder_role_id: int | None = None
    user_role_id: int | None = None
    matching_purpose_id: int | None = None
    time_commitment_id: int | None = None
    city_id: int | None = None
    state_id: int | None = None
    linkedin_profile_id: int | None = None


class CursorPayload(BaseModel):
    score: float
    candidate_id: int
    issued_at: datetime
