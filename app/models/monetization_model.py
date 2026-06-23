from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    tier = Column(String(20), nullable=False, index=True)
    currency_code = Column(String(3), nullable=False)
    price_minor = Column(Integer, nullable=False, default=0)
    billing_interval_months = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("tier IN ('free', 'premium')", name="chk_pricing_plans_tier"),
        CheckConstraint("price_minor >= 0", name="chk_pricing_plans_price_minor"),
        CheckConstraint("billing_interval_months > 0", name="chk_pricing_plans_billing_interval"),
    )


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subscription_id", name="uq_user_subscriptions_provider_subscription"),
        CheckConstraint("provider IN ('stripe', 'razorpay', 'xpay')", name="chk_user_subscriptions_provider"),
        CheckConstraint(
            "status IN ('incomplete', 'trialing', 'active', 'grace', 'past_due', 'canceled', 'expired')",
            name="chk_user_subscriptions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("pricing_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    provider = Column(String(20), nullable=False, index=True)
    provider_customer_id = Column(Text, nullable=True)
    provider_subscription_id = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    current_period_start = Column(TIMESTAMP(timezone=True), nullable=True)
    current_period_end = Column(TIMESTAMP(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    canceled_at = Column(TIMESTAMP(timezone=True), nullable=True)
    trial_end_at = Column(TIMESTAMP(timezone=True), nullable=True)
    subscription_metadata = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BillingWebhookEvent(Base):
    __tablename__ = "billing_webhook_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_billing_webhook_events_provider_event"),
        CheckConstraint("provider IN ('stripe', 'razorpay', 'xpay')", name="chk_billing_webhook_events_provider"),
        CheckConstraint(
            "processing_status IN ('received', 'processed', 'failed')",
            name="chk_billing_webhook_events_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(20), nullable=False, index=True)
    provider_event_id = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)
    payload = Column(JSON, nullable=False)
    received_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    processing_status = Column(String(20), nullable=False, default="received")
    error_message = Column(Text, nullable=True)


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"
    __table_args__ = (
        CheckConstraint("tier IN ('free', 'premium')", name="chk_user_entitlements_tier"),
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tier = Column(String(20), nullable=False, default="free", index=True)
    ads_enabled = Column(Boolean, nullable=False, default=True)
    matchmaking_swipe_limit = Column(Integer, nullable=True, default=10)
    unlimited_swipes = Column(Boolean, nullable=False, default=False)
    investor_intro_access = Column(Boolean, nullable=False, default=False)
    curated_events_access = Column(Boolean, nullable=False, default=False)
    valid_from = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    valid_until = Column(TIMESTAMP(timezone=True), nullable=True)
    source_subscription_id = Column(Integer, ForeignKey("user_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    computed_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SwipeQuotaCycle(Base):
    __tablename__ = "swipe_quota_cycles"
    __table_args__ = (
        UniqueConstraint("user_id", "mode", "period_start", "period_end", name="uq_swipe_quota_cycles_user_mode_period"),
        CheckConstraint("mode IN ('matchmaking')", name="chk_swipe_quota_cycles_mode"),
        CheckConstraint("free_swipe_limit >= 0", name="chk_swipe_quota_cycles_limit"),
        CheckConstraint("swipes_used >= 0", name="chk_swipe_quota_cycles_swipes_used"),
        CheckConstraint("period_end >= period_start", name="chk_swipe_quota_cycles_period"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(20), nullable=False, default="matchmaking", index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    free_swipe_limit = Column(Integer, nullable=False, default=10)
    swipes_used = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SwipeEvent(Base):
    __tablename__ = "swipe_events"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_swipe_events_user_request"),
        CheckConstraint("mode IN ('discover', 'matchmaking')", name="chk_swipe_events_mode"),
        CheckConstraint("action IN ('like', 'pass', 'save', 'unsave')", name="chk_swipe_events_action"),
        CheckConstraint("user_id <> target_user_id", name="chk_swipe_events_not_self"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)
    is_counted = Column(Boolean, nullable=False, default=False)
    counted_swipe_number = Column(Integer, nullable=True)
    quota_cycle_id = Column(Integer, ForeignKey("swipe_quota_cycles.id", ondelete="SET NULL"), nullable=True, index=True)
    request_id = Column(String(36), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class AdTrigger(Base):
    __tablename__ = "ad_triggers"
    __table_args__ = (
        CheckConstraint("trigger_after_swipe_number > 0", name="chk_ad_triggers_swipe_number"),
        CheckConstraint("status IN ('pending', 'served', 'skipped', 'failed')", name="chk_ad_triggers_status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    swipe_event_id = Column(Integer, ForeignKey("swipe_events.id", ondelete="CASCADE"), nullable=False, index=True)
    quota_cycle_id = Column(Integer, ForeignKey("swipe_quota_cycles.id", ondelete="SET NULL"), nullable=True, index=True)
    trigger_after_swipe_number = Column(Integer, nullable=False)
    ad_network = Column(Text, nullable=True)
    ad_placement = Column(Text, nullable=False, default="matchmaking_interstitial")
    status = Column(String(20), nullable=False, default="pending", index=True)
    served_at = Column(TIMESTAMP(timezone=True), nullable=True)
    acknowledged_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class InvestorIntroRequest(Base):
    __tablename__ = "investor_intro_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested', 'under_review', 'approved', 'rejected', 'introduced', 'closed')",
            name="chk_investor_intro_requests_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="requested", index=True)
    summary = Column(Text, nullable=True)
    target_focus = Column(Text, nullable=True)
    notes_internal = Column(Text, nullable=True)
    assigned_to = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CuratedEvent(Base):
    __tablename__ = "curated_events"
    __table_args__ = (
        CheckConstraint("capacity IS NULL OR capacity > 0", name="chk_curated_events_capacity"),
        CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="chk_curated_events_end_after_start"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    country_code = Column(String(2), nullable=True)
    starts_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    ends_at = Column(TIMESTAMP(timezone=True), nullable=True)
    capacity = Column(Integer, nullable=True)
    is_premium_only = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CuratedEventRegistration(Base):
    __tablename__ = "curated_event_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_curated_event_registrations_event_user"),
        CheckConstraint(
            "status IN ('registered', 'waitlisted', 'attended', 'cancelled', 'no_show')",
            name="chk_curated_event_registrations_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("curated_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="registered", index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
