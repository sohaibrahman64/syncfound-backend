from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.monetization_model import (
    BillingWebhookEvent,
    CuratedEvent,
    CuratedEventRegistration,
    InvestorIntroRequest,
    PricingPlan,
    UserEntitlement,
    UserSubscription,
)
from app.models.user_model import User
from app.schemas.monetization_schema import (
    BillingSubscriptionEventRequest,
    BillingWebhookResponse,
    CuratedEventRegistrationResponse,
    CuratedEventResponse,
    InvestorIntroRequestCreate,
    InvestorIntroRequestResponse,
    PricingPlanResponse,
    UserEntitlementResponse,
    UserSubscriptionResponse,
)
from app.services.firebase_service import verify_firebase_id_token

router = APIRouter(prefix="/api/v1", tags=["Monetization"])


def _get_authenticated_user(authorization: str, db: Session) -> User:
    token_prefix = "Bearer "
    if not authorization or not authorization.startswith(token_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    firebase_token = authorization[len(token_prefix):].strip()
    if not firebase_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase token.",
        )

    try:
        decoded_token = verify_firebase_id_token(firebase_token)
    except (ValueError, firebase_exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token.",
        ) from exc

    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain a valid uid.",
        )

    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


def _upsert_free_entitlement_if_missing(db: Session, user_id: int) -> UserEntitlement:
    entitlement = db.query(UserEntitlement).filter(UserEntitlement.user_id == user_id).first()
    if entitlement is not None:
        return entitlement

    entitlement = UserEntitlement(
        user_id=user_id,
        tier="free",
        ads_enabled=True,
        matchmaking_swipe_limit=9,
        unlimited_swipes=False,
        investor_intro_access=False,
        curated_events_access=False,
        valid_from=datetime.now(timezone.utc),
        valid_until=None,
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def _sync_entitlement_from_subscription(db: Session, user_id: int, subscription: UserSubscription, plan: PricingPlan) -> UserEntitlement:
    entitlement = db.query(UserEntitlement).filter(UserEntitlement.user_id == user_id).first()
    if entitlement is None:
        entitlement = UserEntitlement(user_id=user_id)
        db.add(entitlement)

    is_live = subscription.status in {"active", "trialing", "grace"}
    if is_live and plan.tier == "premium":
        entitlement.tier = "premium"
        entitlement.ads_enabled = False
        entitlement.matchmaking_swipe_limit = None
        entitlement.unlimited_swipes = True
        entitlement.investor_intro_access = True
        entitlement.curated_events_access = True
        entitlement.valid_from = datetime.now(timezone.utc)
        entitlement.valid_until = subscription.current_period_end
        entitlement.source_subscription_id = subscription.id
    else:
        entitlement.tier = "free"
        entitlement.ads_enabled = True
        entitlement.matchmaking_swipe_limit = 10
        entitlement.unlimited_swipes = False
        entitlement.investor_intro_access = False
        entitlement.curated_events_access = False
        entitlement.valid_from = datetime.now(timezone.utc)
        entitlement.valid_until = None
        entitlement.source_subscription_id = None

    entitlement.computed_at = datetime.now(timezone.utc)
    return entitlement


@router.get("/pricing/plans", response_model=list[PricingPlanResponse])
def get_pricing_plans(db: Session = Depends(get_db)):
    return (
        db.query(PricingPlan)
        .filter(PricingPlan.is_active.is_(True))
        .order_by(PricingPlan.price_minor.asc(), PricingPlan.id.asc())
        .all()
    )


@router.get("/users/me/entitlements", response_model=UserEntitlementResponse)
def get_my_entitlements(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    entitlement = _upsert_free_entitlement_if_missing(db=db, user_id=user.id)
    db.commit()
    db.refresh(entitlement)
    return entitlement


@router.get("/users/me/subscriptions", response_model=list[UserSubscriptionResponse])
def get_my_subscriptions(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    return (
        db.query(UserSubscription)
        .filter(UserSubscription.user_id == user.id)
        .order_by(UserSubscription.created_at.desc())
        .all()
    )


@router.post("/billing/webhooks/{provider}", response_model=BillingWebhookResponse)
def ingest_billing_webhook(
    payload: BillingSubscriptionEventRequest,
    provider: str = Path(..., pattern="^(stripe|razorpay|xpay)$"),
    db: Session = Depends(get_db),
):
    duplicate_event = False

    if provider not in {"stripe", "razorpay", "xpay"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider.")

    existing_event = (
        db.query(BillingWebhookEvent)
        .filter(
            BillingWebhookEvent.provider == provider,
            BillingWebhookEvent.provider_event_id == payload.provider_event_id,
        )
        .first()
    )
    if existing_event is not None:
        return BillingWebhookResponse(message="Webhook already processed.", duplicate_event=True)

    plan = db.query(PricingPlan).filter(PricingPlan.code == payload.plan_code, PricingPlan.is_active.is_(True)).first()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active plan not found.")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    webhook_event = BillingWebhookEvent(
        provider=provider,
        provider_event_id=payload.provider_event_id,
        event_type=payload.event_type,
        payload=payload.model_dump(),
        processing_status="received",
    )
    db.add(webhook_event)

    subscription = None
    if payload.provider_subscription_id:
        subscription = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.provider == provider,
                UserSubscription.provider_subscription_id == payload.provider_subscription_id,
            )
            .first()
        )

    if subscription is None:
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            provider=provider,
            provider_customer_id=payload.provider_customer_id,
            provider_subscription_id=payload.provider_subscription_id,
            status=payload.status,
            current_period_start=payload.current_period_start,
            current_period_end=payload.current_period_end,
            cancel_at_period_end=payload.cancel_at_period_end,
            canceled_at=payload.canceled_at,
            trial_end_at=payload.trial_end_at,
            subscription_metadata=payload.metadata,
        )
        db.add(subscription)
    else:
        subscription.user_id = user.id
        subscription.plan_id = plan.id
        subscription.provider_customer_id = payload.provider_customer_id
        subscription.status = payload.status
        subscription.current_period_start = payload.current_period_start
        subscription.current_period_end = payload.current_period_end
        subscription.cancel_at_period_end = payload.cancel_at_period_end
        subscription.canceled_at = payload.canceled_at
        subscription.trial_end_at = payload.trial_end_at
        subscription.subscription_metadata = payload.metadata

    try:
        db.flush()
        _sync_entitlement_from_subscription(db=db, user_id=user.id, subscription=subscription, plan=plan)
        webhook_event.processing_status = "processed"
        webhook_event.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(subscription)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate subscription state.") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process webhook: {str(exc)}") from exc

    return BillingWebhookResponse(
        message="Webhook processed successfully.",
        duplicate_event=duplicate_event,
        subscription_id=subscription.id,
    )


@router.post("/users/me/investor-intro-requests", response_model=InvestorIntroRequestResponse)
def create_investor_intro_request(
    payload: InvestorIntroRequestCreate,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    entitlement = _upsert_free_entitlement_if_missing(db=db, user_id=user.id)

    if not entitlement.investor_intro_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Investor introductions are available for premium users only.",
        )

    intro_request = InvestorIntroRequest(
        user_id=user.id,
        status="requested",
        summary=payload.summary,
        target_focus=payload.target_focus,
    )
    db.add(intro_request)
    db.commit()
    db.refresh(intro_request)
    return intro_request


@router.get("/curated-events", response_model=list[CuratedEventResponse])
def get_curated_events(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    entitlement = _upsert_free_entitlement_if_missing(db=db, user_id=user.id)

    query = db.query(CuratedEvent).filter(CuratedEvent.is_active.is_(True))
    if not entitlement.curated_events_access:
        query = query.filter(CuratedEvent.is_premium_only.is_(False))

    db.commit()
    return query.order_by(CuratedEvent.starts_at.asc(), CuratedEvent.id.asc()).all()


@router.post("/curated-events/{event_id}/registrations", response_model=CuratedEventRegistrationResponse)
def register_for_curated_event(
    event_id: int,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    entitlement = _upsert_free_entitlement_if_missing(db=db, user_id=user.id)

    event = db.query(CuratedEvent).filter(CuratedEvent.id == event_id, CuratedEvent.is_active.is_(True)).first()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    if event.is_premium_only and not entitlement.curated_events_access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Premium event access required.")

    existing = (
        db.query(CuratedEventRegistration)
        .filter(
            CuratedEventRegistration.event_id == event.id,
            CuratedEventRegistration.user_id == user.id,
        )
        .first()
    )
    if existing is not None:
        return existing

    registration = CuratedEventRegistration(
        event_id=event.id,
        user_id=user.id,
        status="registered",
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration
