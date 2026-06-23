from datetime import datetime

from pydantic import BaseModel, Field


class PricingPlanResponse(BaseModel):
    id: int
    code: str
    name: str
    tier: str
    currency_code: str
    price_minor: int
    billing_interval_months: int
    is_active: bool

    class Config:
        from_attributes = True


class UserSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    provider: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    status: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool
    canceled_at: datetime | None = None
    trial_end_at: datetime | None = None
    metadata: dict = Field(default_factory=dict, alias="subscription_metadata")

    class Config:
        from_attributes = True
        populate_by_name = True


class UserEntitlementResponse(BaseModel):
    user_id: int
    tier: str
    ads_enabled: bool
    matchmaking_swipe_limit: int | None = None
    unlimited_swipes: bool
    investor_intro_access: bool
    curated_events_access: bool
    valid_from: datetime
    valid_until: datetime | None = None

    class Config:
        from_attributes = True


class BillingSubscriptionEventRequest(BaseModel):
    provider_event_id: str
    event_type: str
    user_id: int = Field(gt=0)
    plan_code: str
    status: str
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False
    canceled_at: datetime | None = None
    trial_end_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class BillingWebhookResponse(BaseModel):
    message: str
    duplicate_event: bool = False
    subscription_id: int | None = None


class InvestorIntroRequestCreate(BaseModel):
    summary: str | None = None
    target_focus: str | None = None


class InvestorIntroRequestResponse(BaseModel):
    id: int
    user_id: int
    status: str
    summary: str | None = None
    target_focus: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CuratedEventResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    city: str | None = None
    country_code: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    capacity: int | None = None
    is_premium_only: bool
    is_active: bool

    class Config:
        from_attributes = True


class CuratedEventRegistrationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
