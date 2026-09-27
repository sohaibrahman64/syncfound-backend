from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from decimal import Decimal
import re
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, status
from fastapi.responses import RedirectResponse
from firebase_admin import exceptions as firebase_exceptions
import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.city_model import City
from app.models.country_new_model import CountryNew
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
from app.models.user_profile_model import UserProfile
from app.schemas.monetization_schema import (
    BillingCheckoutSessionRequest,
    BillingCheckoutSessionResponse,
    BillingSubscriptionEventRequest,
    BillingWebhookResponse,
    CuratedEventRegistrationResponse,
    CuratedEventResponse,
    InvestorIntroRequestCreate,
    InvestorIntroRequestResponse,
    PaywallPricingResponse,
    PricingPlanResponse,
    UserEntitlementResponse,
    UserSubscriptionResponse,
)
from app.services.firebase_service import verify_firebase_id_token

router = APIRouter(prefix="/api/v1", tags=["Monetization"])

INDIA_ISO2 = "IN"
PAYU_PROVIDER = "payu"


def _split_first_name(full_name: str | None) -> str:
    normalized = (full_name or "").strip()
    if normalized:
        return normalized.split()[0]
    return "User"


def _format_payu_amount(amount_minor: int) -> str:
    return format(Decimal(amount_minor) / Decimal("100"), ".2f")


def _build_payu_hash(
    merchant_key: str,
    merchant_salt: str,
    txnid: str,
    amount: str,
    productinfo: str,
    firstname: str,
    email: str,
) -> str:
    hash_sequence = [
        merchant_key,
        txnid,
        amount,
        productinfo,
        firstname,
        email,
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        merchant_salt,
    ]
    hash_string = "|".join(hash_sequence)
    return hashlib.sha512(hash_string.encode("utf-8")).hexdigest()


def _build_payu_provider_payload(
    checkout_session_id: str,
    plan: PricingPlan,
    email: str,
    mobile: str,
    full_name: str | None,
) -> tuple[str, dict[str, str]]:
    merchant_key = os.getenv("PAYU_MERCHANT_KEY", "").strip()
    merchant_salt = os.getenv("PAYU_MERCHANT_SALT", "").strip()
    success_url = os.getenv("PAYU_SUCCESS_URL", "").strip()
    failure_url = os.getenv("PAYU_FAILURE_URL", "").strip()
    action_url = os.getenv("PAYU_HOSTED_CHECKOUT_BASE_URL", "https://secure.payu.in/_payment").strip()

    if not merchant_key or not merchant_salt or not success_url or not failure_url or not action_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PayU checkout configuration is incomplete.",
        )

    txnid = checkout_session_id
    amount = _format_payu_amount(plan.price_minor)
    firstname = _split_first_name(full_name)
    productinfo = plan.name
    hash_value = _build_payu_hash(
        merchant_key=merchant_key,
        merchant_salt=merchant_salt,
        txnid=txnid,
        amount=amount,
        productinfo=productinfo,
        firstname=firstname,
        email=email,
    )

    post_data_fields = {
        "key": merchant_key,
        "txnid": txnid,
        "amount": amount,
        "firstname": firstname,
        "productinfo": productinfo,
        "email": email,
        "phone": mobile,
        "surl": success_url,
        "furl": failure_url,
        "hash": hash_value,
    }
    post_data = urlencode(post_data_fields)

    return action_url, {
        "flow": "webview_post",
        "method": "POST",
        "action_url": action_url,
        "post_data": post_data,
        "txnid": txnid,
        "surl": success_url,
        "furl": failure_url,
    }


def _get_frontend_callback_url_or_500(kind: str) -> str:
    env_key = f"PAYU_FRONTEND_{kind.upper()}_URL"
    callback_url = os.getenv(env_key, "").strip()
    if not callback_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing {env_key} configuration for PayU callback redirection.",
        )
    return callback_url


def _merge_callback_fields(request: Request, payload: dict[str, str], fallback_status: str) -> dict[str, str]:
    status_value = (payload.get("status") or fallback_status).strip().lower()
    txnid = (payload.get("txnid") or "").strip()
    error_code = (payload.get("error_code") or payload.get("error") or "").strip()
    error_message = (
        payload.get("error_message")
        or payload.get("error_Message")
        or payload.get("field9")
        or ""
    ).strip()

    merged: dict[str, str] = {
        "status": status_value,
    }
    if txnid:
        merged["checkout_session_id"] = txnid
        merged["txnid"] = txnid
    if error_code:
        merged["error_code"] = error_code
    if error_message:
        merged["error_message"] = error_message

    # Preserve upstream fields for troubleshooting on frontend callback page.
    for key in ("mihpayid", "mode", "amount", "productinfo", "email", "phone"):
        value = (payload.get(key) or "").strip()
        if value:
            merged[key] = value

    # Preserve existing query params from initial callback URL (if any).
    for key, value in request.query_params.items():
        if key not in merged and value:
            merged[key] = value

    return merged


def _redirect_to_frontend_callback(base_url: str, params: dict[str, str]) -> RedirectResponse:
    separator = "&" if "?" in base_url else "?"
    return RedirectResponse(url=f"{base_url}{separator}{urlencode(params)}", status_code=status.HTTP_302_FOUND)


def _payu_reverse_hash(payload: dict[str, str], merchant_salt: str) -> str:
    additional_charges = payload.get("additionalCharges") or payload.get("additional_charges") or ""
    merchant_key = (payload.get("key") or os.getenv("PAYU_MERCHANT_KEY", "")).strip()
    values = [
        payload.get("status", ""),
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        payload.get("email", ""),
        payload.get("firstname", ""),
        payload.get("productinfo", ""),
        payload.get("amount", ""),
        payload.get("txnid", ""),
        merchant_key,
    ]
    hash_string = "|".join([merchant_salt, *values])
    if additional_charges:
        hash_string = "|".join([additional_charges, hash_string])
    return hashlib.sha512(hash_string.encode("utf-8")).hexdigest()

def _payu_reverse_hash_new(payload: dict[str, str], merchant_salt: str) -> str:
    additional_charges = (
        payload.get("additionalCharges")
        or payload.get("additional_charges")
        or ""
    )

    merchant_key = (
        payload.get("key")
        or os.getenv("PAYU_MERCHANT_KEY", "")
    ).strip()

    values = [
        payload.get("status", ""),
        "",
        "",
        "",
        "",
        "",
        payload.get("udf5"),
        payload.get("udf4", ""),
        payload.get("udf3", ""),
        payload.get("udf2", ""),
        payload.get("udf1", ""),
        payload.get("email", ""),
        payload.get("firstname", ""),
        payload.get("productinfo", ""),
        payload.get("amount", ""),
        payload.get("txnid", ""),
        merchant_key,
    ]
    hash_string = "|".join([merchant_salt, *values])

    if additional_charges:
        hash_string = "|".join([additional_charges, hash_string])

    # print("PAYU REVERSE HASH STRING:")
    # print(hash_string.replace(merchant_salt, "<SALT>"))

    calculated_hash = hashlib.sha512(
        hash_string.encode("utf-8")
    ).hexdigest()

    # print("PAYU POSTED HASH:", payload.get("hash"))
    # print("PAYU CALCULATED HASH:", calculated_hash)

    return calculated_hash


def _validate_payu_response_hash(payload: dict[str, str]) -> bool:
    posted_hash = (payload.get("hash") or "").strip().lower()
    merchant_salt = os.getenv("PAYU_MERCHANT_SALT", "").strip()
    if not posted_hash or not merchant_salt:
        return False
    calculated_hash = _payu_reverse_hash_new(payload, merchant_salt)
    return hmac.compare_digest(posted_hash, calculated_hash)


def _verify_payu_transaction(payload: dict[str, str]) -> bool:
    verify_url = os.getenv("PAYU_VERIFY_URL", "").strip()
    if not verify_url:
        action_url = os.getenv("PAYU_HOSTED_CHECKOUT_BASE_URL", "https://secure.payu.in/_payment")
        verify_url = "https://test.payu.in/merchant/postservice.php?form=2" if "test." in action_url else "https://info.payu.in/merchant/postservice.php?form=2"

    merchant_key = os.getenv("PAYU_MERCHANT_KEY", "").strip()
    merchant_salt = os.getenv("PAYU_MERCHANT_SALT", "").strip()
    txnid = payload.get("txnid", "")
    verify_hash = hashlib.sha512(
        f"{merchant_key}|verify_payment|{txnid}|{merchant_salt}".encode("utf-8")
    ).hexdigest()

    try:
        response = requests.post(
            verify_url,
            data={
                "key": merchant_key,
                "command": "verify_payment",
                "var1": txnid,
                "hash": verify_hash,
            },
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
    except (requests.RequestException, ValueError):
        return False

    transaction_details = result.get("transaction_details", {}) if isinstance(result, dict) else {}
    transaction = transaction_details.get(txnid, {}) if isinstance(transaction_details, dict) else {}
    return bool(
        isinstance(result, dict)
        and str(result.get("status")) == "1"
        and str(transaction.get("status", "")).lower() == "success"
    )


def _record_payu_event(db: Session, event_id: str, event_type: str, payload: dict[str, str]) -> None:
    existing = (
        db.query(BillingWebhookEvent)
        .filter(
            BillingWebhookEvent.provider == PAYU_PROVIDER,
            BillingWebhookEvent.provider_event_id == event_id,
        )
        .first()
    )
    if existing is None:
        db.add(
            BillingWebhookEvent(
                provider=PAYU_PROVIDER,
                provider_event_id=event_id,
                event_type=event_type,
                payload=payload,
                processing_status="processed",
                processed_at=datetime.now(timezone.utc),
            )
        )

def _normalize_product_info(value: str) -> str:
    value = (value or "").strip().lower()

    # Remove parentheses
    value = re.sub(r"[()]", "", value)

    # Collapse multiple whitespace characters
    value = re.sub(r"\s+", " ", value)

    return value


def _activate_payu_subscription(db: Session, payload: dict[str, str]) -> None:
    email = (payload.get("email") or "").strip().lower()
    txnid = (payload.get("txnid") or "").strip()
    productinfo = (payload.get("productinfo") or "").strip()
    normalized_productinfo = _normalize_product_info(productinfo)
    amount_minor = int((Decimal(payload.get("amount", "0")) * 100).quantize(Decimal("1")))

    user = db.query(User).filter(User.email == email).first() if email else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayU response user could not be matched.")

    # plan = (
    #     db.query(PricingPlan)
    #     .filter(
    #         PricingPlan.is_active.is_(True),
    #         PricingPlan.tier == "premium",
    #         PricingPlan.price_minor == amount_minor,
    #         PricingPlan.name == productinfo,
    #     )
    #     .first()
    # )

    plan = (
    db.query(PricingPlan)
        .filter(
            PricingPlan.is_active.is_(True),
            PricingPlan.tier == "premium",
            PricingPlan.price_minor == amount_minor,
        )
        .all()
    )

    plan = next(
        (
            p for p in plan
            if _normalize_product_info(p.name) == normalized_productinfo
        ),
        None,
    )

    if plan is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PayU response plan could not be matched.")

    subscription = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.provider == PAYU_PROVIDER,
            UserSubscription.provider_subscription_id == txnid,
        )
        .first()
    )
    if subscription is None:
        period_start = datetime.now(timezone.utc)
        subscription = UserSubscription(
            user_id=user.id,
            plan_id=plan.id,
            provider=PAYU_PROVIDER,
            provider_customer_id=None,
            provider_subscription_id=txnid,
            status="active",
            current_period_start=period_start,
            current_period_end=period_start + timedelta(days=30 * plan.billing_interval_months),
            subscription_metadata={"payu_transaction": payload},
        )
        db.add(subscription)
        db.flush()
    else:
        subscription.status = "active"
        subscription.subscription_metadata = {"payu_transaction": payload}

    _sync_entitlement_from_subscription(db=db, user_id=user.id, subscription=subscription, plan=plan)


@router.api_route("/billing/payu/success", methods=["GET", "POST"])
async def payu_success_callback(request: Request, db: Session = Depends(get_db)):
    payload: dict[str, str]
    if request.method == "POST":
        form = await request.form()
        payload = {key: str(value) for key, value in form.items()}
    else:
        payload = {key: value for key, value in request.query_params.items()}

    frontend_url = _get_frontend_callback_url_or_500(kind="success")
    merged = _merge_callback_fields(request=request, payload=payload, fallback_status="success")
    event_id = f"payu-success:{payload.get('txnid', '')}"
    try:
        if not _validate_payu_response_hash(payload):
            _record_payu_event(db=db, event_id=event_id, event_type="payu.payment.invalid_hash", payload=payload)
            db.commit()
            merged.update({"status": "failed", "error_code": "invalid_hash", "error_message": "Payment response validation failed."})
            return _redirect_to_frontend_callback(base_url=frontend_url, params=merged)
        if not _verify_payu_transaction(payload):
            _record_payu_event(db=db, event_id=event_id, event_type="payu.payment.verification_failed", payload=payload)
            db.commit()
            merged.update({"status": "pending", "error_code": "verification_failed", "error_message": "Payment is awaiting verification."})
            return _redirect_to_frontend_callback(base_url=frontend_url, params=merged)
        _activate_payu_subscription(db=db, payload=payload)
        _record_payu_event(db=db, event_id=event_id, event_type="payu.payment.success", payload=payload)
        db.commit()
    except HTTPException as exc:
        db.rollback()
        merged.update({"status": "failed", "error_code": "payment_processing_failed", "error_message": exc.detail})
    except Exception:
        db.rollback()
        merged.update({"status": "failed", "error_code": "payment_processing_failed", "error_message": "Payment processing failed."})
    return _redirect_to_frontend_callback(base_url=frontend_url, params=merged)


@router.api_route("/billing/payu/failure", methods=["GET", "POST"])
async def payu_failure_callback(request: Request, db: Session = Depends(get_db)):
    payload: dict[str, str]
    if request.method == "POST":
        form = await request.form()
        payload = {key: str(value) for key, value in form.items()}
    else:
        payload = {key: value for key, value in request.query_params.items()}

    frontend_url = _get_frontend_callback_url_or_500(kind="failure")
    merged = _merge_callback_fields(request=request, payload=payload, fallback_status="failed")
    event_id = f"payu-failure:{payload.get('txnid') or uuid4().hex}"
    _record_payu_event(db=db, event_id=event_id, event_type="payu.payment.failed", payload=payload)
    db.commit()
    return _redirect_to_frontend_callback(base_url=frontend_url, params=merged)

@router.get("/billing/payu/status")
def get_payu_payment_status(
    checkout_session_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    success_event = (
        db.query(BillingWebhookEvent)
        .filter(
            BillingWebhookEvent.provider == PAYU_PROVIDER,
            BillingWebhookEvent.provider_event_id == f"payu-success:{checkout_session_id}",
        )
        .first()
    )
    failure_event = (
        db.query(BillingWebhookEvent)
        .filter(
            BillingWebhookEvent.provider == PAYU_PROVIDER,
            BillingWebhookEvent.provider_event_id == f"payu-failure:{checkout_session_id}",
        )
        .first()
    )
    event = success_event or failure_event
    if event is None:
        return {
            "checkout_session_id": checkout_session_id,
            "status": "pending",
            "tier": "free",
            "message": "Payment callback has not been received yet.",
        }

    payload = event.payload or {}
    email = (payload.get("email") or "").strip().lower()
    user = db.query(User).filter(User.email == email).first() if email else None
    entitlement = db.query(UserEntitlement).filter(UserEntitlement.user_id == user.id).first() if user else None

    if event.event_type == "payu.payment.success" and entitlement and entitlement.tier == "premium":
        final_status = "success"
    elif event.event_type == "payu.payment.verification_failed":
        final_status = "pending"
    else:
        final_status = "failed"

    return {
        "checkout_session_id": checkout_session_id,
        "status": final_status,
        "tier": entitlement.tier if entitlement else "free",
        "error_code": payload.get("error_code"),
        "error_message": payload.get("error_message"),
        "txnid": payload.get("txnid"),
        "mihpayid": payload.get("mihpayid"),
    }

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


def _get_india_country_or_404(db: Session) -> CountryNew:
    india_country = db.query(CountryNew).filter(CountryNew.iso2 == INDIA_ISO2).first()
    if india_country is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="India country record not found.")
    return india_country


def _get_user_country_id(db: Session, user_id: int) -> int | None:
    return (
        db.query(City.country_id)
        .join(UserProfile, UserProfile.city_id == City.id)
        .filter(UserProfile.user_id == user_id)
        .scalar()
    )


def _resolve_provider(user_country_id: int | None, india_country_id: int) -> str:
    # XPay is paused; route all checkouts to PayU for now.
    return PAYU_PROVIDER


@router.get("/pricing/plans", response_model=list[PricingPlanResponse])
def get_pricing_plans(db: Session = Depends(get_db)):
    return (
        db.query(PricingPlan)
        .filter(PricingPlan.is_active.is_(True))
        .order_by(PricingPlan.price_minor.asc(), PricingPlan.id.asc())
        .all()
    )


@router.get("/users/me/paywall/pricing", response_model=PaywallPricingResponse)
def get_paywall_pricing(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    india_country = _get_india_country_or_404(db=db)
    user_country_id = _get_user_country_id(db=db, user_id=user.id)

    is_indian_user = user_country_id == india_country.id
    currency_code = "INR" if is_indian_user else "USD"

    plans = (
        db.query(PricingPlan)
        .filter(
            PricingPlan.is_active.is_(True),
            PricingPlan.currency_code == currency_code,
        )
        .order_by(PricingPlan.price_minor.asc(), PricingPlan.id.asc())
        .all()
    )

    return PaywallPricingResponse(
        user_id=user.id,
        user_country_id=user_country_id,
        india_country_id=india_country.id,
        is_indian_user=is_indian_user,
        currency_code=currency_code,
        plans=plans,
    )


@router.post("/users/me/billing/checkout-session", response_model=BillingCheckoutSessionResponse)
def create_billing_checkout_session(
    payload: BillingCheckoutSessionRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    india_country = _get_india_country_or_404(db=db)
    user_country_id = _get_user_country_id(db=db, user_id=user.id)

    is_indian_user = user_country_id == india_country.id
    provider = _resolve_provider(user_country_id=user_country_id, india_country_id=india_country.id)

    plan = (
        db.query(PricingPlan)
        .filter(
            PricingPlan.code == payload.plan_code,
            PricingPlan.is_active.is_(True),
        )
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active plan not found.")

    if plan.tier != "premium":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checkout is available for premium plans only.")

    if plan.currency_code not in {"INR", "USD"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid plan currency for checkout. Supported currencies are INR and USD.",
        )

    checkout_email = (user.email or payload.email or "").strip()
    checkout_mobile = (user.mobile or payload.mobile or "").strip()
    missing_fields: list[str] = []
    if not checkout_email:
        missing_fields.append("email")
    if not checkout_mobile:
        missing_fields.append("mobile")
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "PayU checkout requires contact details. "
                f"Missing: {', '.join(missing_fields)}. "
                "Provide these fields in the checkout request or update user profile data."
            ),
        )

    checkout_session_id = f"chk_{uuid4().hex[:16]}"
    checkout_url, provider_payload = _build_payu_provider_payload(
        checkout_session_id=checkout_session_id,
        plan=plan,
        email=checkout_email,
        mobile=checkout_mobile,
        full_name=user.full_name,
    )

    return BillingCheckoutSessionResponse(
        user_id=user.id,
        user_country_id=user_country_id,
        india_country_id=india_country.id,
        is_indian_user=is_indian_user,
        provider=provider,
        plan_id=plan.id,
        plan_code=plan.code,
        currency_code=plan.currency_code,
        amount_minor=plan.price_minor,
        checkout_session_id=checkout_session_id,
        checkout_status="created",
        checkout_url=checkout_url,
        provider_payload=provider_payload,
        message="Checkout session initialized with PayU. Proceed with provider order creation.",
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
    provider: str = Path(..., pattern="^(stripe|razorpay|payu)$"),
    db: Session = Depends(get_db),
):
    duplicate_event = False

    if provider not in {"stripe", "razorpay", "payu"}:
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
