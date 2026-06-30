from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.city_model import City
from app.models.cofounder_role_model import CofounderRole
from app.models.cofounder_skill_model import CofounderSkill
from app.models.country_new_model import CountryNew
from app.models.invite_model import Invite
from app.models.linkedin_profile_model import LinkedInProfile, LinkedInProfileExperience
from app.models.industry_model import Industry
from app.models.match_connection_message_model import MatchConnectionMessage
from app.models.match_model import Match, MatchAction
from app.models.matching_purpose_model import MatchingPurpose
from app.models.monetization_model import AdTrigger, SwipeEvent, SwipeQuotaCycle, UserEntitlement
from app.models.notification_outbox_model import NotificationOutbox
from app.models.user_model import User
from app.models.user_profile_model import (
    UserProfile,
    UserProfileCofounderSkill,
    UserProfileIndustry,
    UserProfileUserSkill,
)
from app.models.user_skill_model import UserSkill
from app.models.user_role_model import UserRole
from app.schemas.matches_schema import (
    MatchActionRequest,
    MatchActionResponse,
    MatchFeedMode,
    MatchItemResponse,
    MatchRow,
    MatchSummaryResponse,
    MatchesFeedResponse,
    PublicProfileResponse,
)
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["Matches"])


FREE_TIER = "free"
PREMIUM_TIER = "premium"
MATCHMAKING_MODE = "matchmaking"
COUNTED_ACTIONS = {"like", "pass"}
DEFAULT_FREE_SWIPE_LIMIT = 9
AD_EVERY_N_SWIPES = 4


def _day_period_bounds(now_utc: datetime) -> tuple[datetime.date, datetime.date]:
    # Quota cycles are tracked by UTC calendar day in the current schema.
    period_start = now_utc.date()
    period_end = now_utc.date()
    return period_start, period_end


def _get_or_create_entitlement(db: Session, user_id: int) -> UserEntitlement:
    entitlement = db.query(UserEntitlement).filter(UserEntitlement.user_id == user_id).first()
    if entitlement is not None:
        return entitlement

    entitlement = UserEntitlement(
        user_id=user_id,
        tier=FREE_TIER,
        ads_enabled=True,
        matchmaking_swipe_limit=DEFAULT_FREE_SWIPE_LIMIT,
        unlimited_swipes=False,
        investor_intro_access=False,
        curated_events_access=False,
        valid_from=datetime.now(timezone.utc),
    )
    db.add(entitlement)
    db.flush()
    return entitlement


def _get_or_create_quota_cycle(db: Session, user_id: int, free_swipe_limit: int, now_utc: datetime) -> SwipeQuotaCycle:
    period_start, period_end = _day_period_bounds(now_utc)
    cycle = (
        db.query(SwipeQuotaCycle)
        .filter(
            SwipeQuotaCycle.user_id == user_id,
            SwipeQuotaCycle.mode == MATCHMAKING_MODE,
            SwipeQuotaCycle.period_start == period_start,
            SwipeQuotaCycle.period_end == period_end,
        )
        .first()
    )
    if cycle is not None:
        if cycle.free_swipe_limit != free_swipe_limit:
            cycle.free_swipe_limit = free_swipe_limit
        return cycle

    cycle = SwipeQuotaCycle(
        user_id=user_id,
        mode=MATCHMAKING_MODE,
        period_start=period_start,
        period_end=period_end,
        free_swipe_limit=free_swipe_limit,
        swipes_used=0,
    )
    db.add(cycle)
    db.flush()
    return cycle


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


def _build_cursor(score: float, candidate_id: int) -> str:
    payload = {
        "score": score,
        "candidate_id": candidate_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _parse_cursor(cursor: str | None) -> tuple[float, int] | None:
    if not cursor:
        return None
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        return float(data["score"]), int(data["candidate_id"])
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor.",
        ) from exc


def _jaccard_score(left: set[int], right: set[int]) -> float:
    if not left and not right:
        return 0.0
    union_size = len(left | right)
    if union_size == 0:
        return 0.0
    return len(left & right) / union_size


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def _is_investor_profile(intent_badge: str | None, user_role: str | None) -> bool:
    intent_normalized = _normalize_label(intent_badge)
    role_normalized = _normalize_label(user_role)
    return "investor" in intent_normalized or "investor" in role_normalized


def _is_purpose_compatible(
    me_intent_badge: str | None,
    candidate_intent_badge: str | None,
    candidate_user_role: str | None,
) -> bool:
    me_intent = _normalize_label(me_intent_badge)
    candidate_intent = _normalize_label(candidate_intent_badge)
    candidate_is_investor = _is_investor_profile(candidate_intent_badge, candidate_user_role)

    if not me_intent:
        return True

    compatibility_map: dict[str, set[str]] = {
        "build a team": {"build a team", "join a team", "connect with investors"},
        "join a team": {"build a team", "join a team"},
        "connect with investors": {"connect with investors"},
    }

    allowed_intents = compatibility_map.get(me_intent)
    if allowed_intents is None:
        return candidate_intent == me_intent

    if candidate_intent in allowed_intents:
        return True

    if "connect with investors" in allowed_intents and candidate_is_investor:
        return True

    return False


def _score_candidate(
    me_profile: UserProfile,
    candidate: MatchRow,
    me_intent_badge: str | None,
    candidate_intent_badge: str | None,
    candidate_user_role: str | None,
    me_user_skills: set[int],
    me_cofounder_skills: set[int],
    me_industries: set[int],
    candidate_user_skills: set[int],
    candidate_cofounder_skills: set[int],
    candidate_industries: set[int],
) -> tuple[float, list[str]]:
    role_component = 0.4
    if me_profile.primary_role_id and candidate.primary_role_id and me_profile.primary_role_id == candidate.primary_role_id:
        role_component = 1.0
    elif me_profile.cofounder_role_id and candidate.cofounder_role_id and me_profile.cofounder_role_id == candidate.cofounder_role_id:
        role_component = 0.8

    looking_for_component = _jaccard_score(me_cofounder_skills, candidate_user_skills)
    complementary_component = _jaccard_score(me_user_skills, candidate_cofounder_skills)

    industry_component = _jaccard_score(me_industries, candidate_industries)

    if me_profile.city_id and candidate.city_id and me_profile.city_id == candidate.city_id:
        location_component = 1.0
    elif me_profile.state_id and candidate.state_id and me_profile.state_id == candidate.state_id:
        location_component = 0.6
    else:
        location_component = 0.2

    if me_profile.time_commitment_id and candidate.time_commitment_id and me_profile.time_commitment_id == candidate.time_commitment_id:
        time_component = 1.0
    else:
        time_component = 0.4

    purpose_component = 1.0 if _is_purpose_compatible(me_intent_badge, candidate_intent_badge, candidate_user_role) else 0.0

    score = round(
        (35 * purpose_component)
        + (35 * looking_for_component)
        + (10 * complementary_component)
        + (10 * role_component)
        + (5 * industry_component)
        + (3 * time_component)
        + (2 * location_component),
        2,
    )

    reasons = [
        f"purpose={purpose_component:.2f}",
        f"role={role_component:.2f}",
        f"looking_for_skills={looking_for_component:.2f}",
        f"complementary_skills={complementary_component:.2f}",
        f"industry={industry_component:.2f}",
        f"location={location_component:.2f}",
        f"time={time_component:.2f}",
    ]
    return score, reasons


@router.get("/users/me/matches", response_model=MatchesFeedResponse)
def get_matches_feed(
    mode: MatchFeedMode = Query(default=MatchFeedMode.matchmaking),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    me_profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if me_profile is None:
        return MatchesFeedResponse(items=[], next_cursor=None)

    acted_target_subquery = (
        db.query(MatchAction.target_user_id)
        .filter(MatchAction.actor_user_id == user.id)
        .distinct()
        .subquery()
    )

    action_state_subquery = (
        db.query(
            MatchAction.target_user_id.label("target_user_id"),
            func.max(case((MatchAction.action == "like", 1), else_=0)).label("liked"),
            func.max(case((MatchAction.action == "pass", 1), else_=0)).label("passed"),
            func.max(case((MatchAction.action == "save", 1), else_=0)).label("saved"),
        )
        .filter(MatchAction.actor_user_id == user.id)
        .group_by(MatchAction.target_user_id)
        .subquery()
    )

    rows = (
        db.query(
            UserProfile.user_id.label("candidate_id"),
            UserProfile.id.label("profile_id"),
            User.full_name.label("display_name"),
            UserProfile.profile_image_uri.label("profile_photo_url"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            City.city_name.label("city"),
            CountryNew.iso2.label("country_code"),
            UserProfile.experience_location.label("location_text"),
            CofounderRole.role_name.label("role"),
            MatchingPurpose.matching_purpose.label("intent_badge"),
            UserProfile.bio.label("experience_summary"),
            UserProfile.startup_idea.label("startup_idea"),
            UserProfile.primary_role_id.label("primary_role_id"),
            UserProfile.cofounder_role_id.label("cofounder_role_id"),
            UserProfile.user_role_id.label("user_role_id"),
            UserProfile.matching_purpose_id.label("matching_purpose_id"),
            UserProfile.time_commitment_id.label("time_commitment_id"),
            UserProfile.city_id.label("city_id"),
            UserProfile.state_id.label("state_id"),
            UserProfile.linkedin_profile_id.label("linkedin_profile_id"),
            func.coalesce(action_state_subquery.c.liked, 0).label("liked"),
            func.coalesce(action_state_subquery.c.passed, 0).label("passed"),
            func.coalesce(action_state_subquery.c.saved, 0).label("saved"),
        )
        .join(User, User.id == UserProfile.user_id)
        .outerjoin(City, City.id == UserProfile.city_id)
        .outerjoin(CountryNew, CountryNew.id == City.country_id)
        .outerjoin(CofounderRole, CofounderRole.id == UserProfile.cofounder_role_id)
        .outerjoin(MatchingPurpose, MatchingPurpose.id == UserProfile.matching_purpose_id)
        .outerjoin(action_state_subquery, action_state_subquery.c.target_user_id == UserProfile.user_id)
        .filter(UserProfile.user_id != user.id)
        .filter(~UserProfile.user_id.in_(acted_target_subquery))
        .all()
    )

    my_user_skill_ids = {
        row.skill_id
        for row in db.query(UserProfileUserSkill.skill_id)
        .filter(UserProfileUserSkill.user_profile_id == me_profile.id)
        .all()
    }
    my_cofounder_skill_ids = {
        row.skill_id
        for row in db.query(UserProfileCofounderSkill.skill_id)
        .filter(UserProfileCofounderSkill.user_profile_id == me_profile.id)
        .all()
    }
    my_industry_ids = {
        row.industry_id
        for row in db.query(UserProfileIndustry.industry_id)
        .filter(UserProfileIndustry.user_profile_id == me_profile.id)
        .all()
    }

    me_intent_badge = None
    if me_profile.matching_purpose_id is not None:
        me_intent_badge = (
            db.query(MatchingPurpose.matching_purpose)
            .filter(MatchingPurpose.id == me_profile.matching_purpose_id)
            .scalar()
        )

    profile_ids = [row.profile_id for row in rows]
    linkedin_profile_ids = [row.linkedin_profile_id for row in rows if row.linkedin_profile_id is not None]

    candidate_user_roles_map: dict[int, str | None] = {}
    candidate_user_skills_map: dict[int, set[int]] = {}
    candidate_user_skill_names_map: dict[int, list[str]] = {}
    candidate_cofounder_skills_map: dict[int, set[int]] = {}
    candidate_cofounder_skill_names_map: dict[int, list[str]] = {}
    candidate_industries_map: dict[int, set[int]] = {}
    candidate_linkedin_summary_map: dict[int, dict[str, object]] = {}
    candidate_linkedin_experiences_map: dict[int, list[dict[str, object]]] = {}

    if profile_ids:
        candidate_role_rows = (
            db.query(UserProfile.id, UserRole.role_name)
            .outerjoin(UserRole, UserRole.id == UserProfile.user_role_id)
            .filter(UserProfile.id.in_(profile_ids))
            .all()
        )
        for profile_id, role_name in candidate_role_rows:
            candidate_user_roles_map[profile_id] = role_name

        candidate_user_skill_rows = (
            db.query(UserProfileUserSkill.user_profile_id, UserSkill.skill_name)
            .join(UserSkill, UserSkill.id == UserProfileUserSkill.skill_id)
            .filter(UserProfileUserSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_name in candidate_user_skill_rows:
            candidate_user_skill_names_map.setdefault(profile_id, []).append(skill_name)

        candidate_user_skill_id_rows = (
            db.query(UserProfileUserSkill.user_profile_id, UserProfileUserSkill.skill_id)
            .filter(UserProfileUserSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_id in candidate_user_skill_id_rows:
            candidate_user_skills_map.setdefault(profile_id, set()).add(skill_id)

        candidate_cofounder_skill_rows = (
            db.query(UserProfileCofounderSkill.user_profile_id, CofounderSkill.skill_name)
            .join(CofounderSkill, CofounderSkill.id == UserProfileCofounderSkill.skill_id)
            .filter(UserProfileCofounderSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_name in candidate_cofounder_skill_rows:
            candidate_cofounder_skill_names_map.setdefault(profile_id, []).append(skill_name)

        candidate_cofounder_skill_id_rows = (
            db.query(UserProfileCofounderSkill.user_profile_id, UserProfileCofounderSkill.skill_id)
            .filter(UserProfileCofounderSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_id in candidate_cofounder_skill_id_rows:
            candidate_cofounder_skills_map.setdefault(profile_id, set()).add(skill_id)

        candidate_industry_rows = (
            db.query(UserProfileIndustry.user_profile_id, UserProfileIndustry.industry_id)
            .filter(UserProfileIndustry.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, industry_id in candidate_industry_rows:
            candidate_industries_map.setdefault(profile_id, set()).add(industry_id)

    if linkedin_profile_ids:
        linkedin_rows = (
            db.query(
                LinkedInProfile.id.label("linkedin_profile_id"),
                LinkedInProfile.user_id.label("user_id"),
                LinkedInProfile.headline.label("headline"),
                LinkedInProfile.current_company.label("current_company"),
                LinkedInProfile.location_full.label("location_full"),
                LinkedInProfile.location_city.label("location_city"),
                LinkedInProfile.location_country_code.label("location_country_code"),
                LinkedInProfile.top_education_school_name.label("top_education_school_name"),
            )
            .filter(LinkedInProfile.id.in_(linkedin_profile_ids))
            .all()
        )
        linkedin_profile_id_to_profile_id: dict[int, int] = {
            row.linkedin_profile_id: row.candidate_profile_id
            for row in db.query(
                UserProfile.id.label("candidate_profile_id"),
                UserProfile.linkedin_profile_id.label("linkedin_profile_id"),
            )
            .filter(UserProfile.linkedin_profile_id.in_(linkedin_profile_ids))
            .all()
        }
        for row in linkedin_rows:
            profile_id = linkedin_profile_id_to_profile_id.get(row.linkedin_profile_id)
            if profile_id is None:
                continue
            candidate_linkedin_summary_map[profile_id] = {
                "headline": row.headline,
                "current_company": row.current_company,
                "location": row.location_full or row.location_city or row.location_country_code,
                "top_education_school_name": row.top_education_school_name,
            }

        linkedin_experience_rows = (
            db.query(
                LinkedInProfileExperience.profile_id.label("profile_id"),
                LinkedInProfileExperience.title.label("title"),
                LinkedInProfileExperience.company.label("company"),
                LinkedInProfileExperience.location.label("location"),
                LinkedInProfileExperience.description.label("description"),
                LinkedInProfileExperience.duration.label("duration"),
                LinkedInProfileExperience.start_year.label("start_year"),
                LinkedInProfileExperience.start_month.label("start_month"),
                LinkedInProfileExperience.end_year.label("end_year"),
                LinkedInProfileExperience.end_month.label("end_month"),
                LinkedInProfileExperience.is_current.label("is_current"),
                LinkedInProfileExperience.company_linkedin_url.label("company_linkedin_url"),
                LinkedInProfileExperience.company_logo_url.label("company_logo_url"),
                LinkedInProfileExperience.employment_type.label("employment_type"),
                LinkedInProfileExperience.location_type.label("location_type"),
            )
            .filter(LinkedInProfileExperience.profile_id.in_(linkedin_profile_ids))
            .order_by(LinkedInProfileExperience.is_current.desc(), LinkedInProfileExperience.id.asc())
            .all()
        )
        for row in linkedin_experience_rows:
            candidate_profile_id = linkedin_profile_id_to_profile_id.get(row.profile_id)
            if candidate_profile_id is None:
                continue
            candidate_linkedin_experiences_map.setdefault(candidate_profile_id, []).append(
                {
                    "title": row.title,
                    "company": row.company,
                    "location": row.location,
                    "description": row.description,
                    "duration": row.duration,
                    "start_year": row.start_year,
                    "start_month": row.start_month,
                    "end_year": row.end_year,
                    "end_month": row.end_month,
                    "is_current": row.is_current,
                    "company_linkedin_url": row.company_linkedin_url,
                    "company_logo_url": row.company_logo_url,
                    "employment_type": row.employment_type,
                    "location_type": row.location_type,
                }
            )

    feed_items: list[MatchItemResponse] = []
    for row in rows:
        candidate_user_role = candidate_user_roles_map.get(row.profile_id)

        if mode == MatchFeedMode.matchmaking and not _is_purpose_compatible(
            me_intent_badge=me_intent_badge,
            candidate_intent_badge=row.intent_badge,
            candidate_user_role=candidate_user_role,
        ):
            continue

        candidate_row = MatchRow(
            candidate_id=row.candidate_id,
            profile_id=row.profile_id,
            display_name=row.display_name,
            profile_photo_url=row.profile_photo_url,
            first_name=row.first_name,
            last_name=row.last_name,
            city=row.city,
            country_code=row.country_code,
            location_text=row.location_text,
            role=row.role,
            intent_badge=row.intent_badge,
            experience_summary=row.experience_summary,
            primary_role_id=row.primary_role_id,
            cofounder_role_id=row.cofounder_role_id,
            matching_purpose_id=row.matching_purpose_id,
            time_commitment_id=row.time_commitment_id,
            city_id=row.city_id,
            state_id=row.state_id,
        )

        if mode == MatchFeedMode.discover:
            score = float(row.candidate_id)
            reasons = ["discover_mode"]
        else:
            score, reasons = _score_candidate(
                me_profile=me_profile,
                candidate=candidate_row,
                me_intent_badge=me_intent_badge,
                candidate_intent_badge=row.intent_badge,
                candidate_user_role=candidate_user_role,
                me_user_skills=my_user_skill_ids,
                me_cofounder_skills=my_cofounder_skill_ids,
                me_industries=my_industry_ids,
                candidate_user_skills=candidate_user_skills_map.get(row.profile_id, set()),
                candidate_cofounder_skills=candidate_cofounder_skills_map.get(row.profile_id, set()),
                candidate_industries=candidate_industries_map.get(row.profile_id, set()),
            )

        feed_items.append(
            MatchItemResponse(
                candidate_id=row.candidate_id,
                display_name=row.display_name or f"{row.first_name or ''} {row.last_name or ''}".strip() or None,
                profile_photo_url=row.profile_photo_url,
                country_code=row.country_code,
                city=row.city,
                location_text=row.location_text,
                user_role=candidate_user_role,
                role=row.role,
                intent_badge=row.intent_badge,
                bio=row.experience_summary,
                experience_summary=row.experience_summary,
                startup_idea=row.startup_idea,
                user_skills=candidate_user_skill_names_map.get(row.profile_id, []),
                cofounder_skills=candidate_cofounder_skill_names_map.get(row.profile_id, []),
                linkedin_headline=candidate_linkedin_summary_map.get(row.profile_id, {}).get("headline") if row.profile_id in candidate_linkedin_summary_map else None,
                linkedin_current_company=candidate_linkedin_summary_map.get(row.profile_id, {}).get("current_company") if row.profile_id in candidate_linkedin_summary_map else None,
                linkedin_location=candidate_linkedin_summary_map.get(row.profile_id, {}).get("location") if row.profile_id in candidate_linkedin_summary_map else None,
                linkedin_top_education_school_name=candidate_linkedin_summary_map.get(row.profile_id, {}).get("top_education_school_name") if row.profile_id in candidate_linkedin_summary_map else None,
                linkedin_experiences=candidate_linkedin_experiences_map.get(row.profile_id, []),
                match_score=score,
                match_reasons=reasons,
                liked=bool(row.liked),
                passed=bool(row.passed),
                saved=bool(row.saved),
            )
        )

    feed_items.sort(key=lambda item: (-item.match_score, item.candidate_id))

    cursor_tuple = None if refresh else _parse_cursor(cursor)
    if cursor_tuple is not None:
        cursor_score, cursor_candidate_id = cursor_tuple
        feed_items = [
            item
            for item in feed_items
            if (item.match_score < cursor_score)
            or (item.match_score == cursor_score and item.candidate_id > cursor_candidate_id)
        ]

    paged_items = feed_items[:limit]

    next_cursor = None
    if len(feed_items) > limit and paged_items:
        last = paged_items[-1]
        next_cursor = _build_cursor(score=last.match_score, candidate_id=last.candidate_id)

    return MatchesFeedResponse(items=paged_items, next_cursor=next_cursor)


@router.post("/users/me/matches/{candidate_id}/actions", response_model=MatchActionResponse)
def post_match_action(
    candidate_id: int,
    payload: MatchActionRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    now_utc = datetime.now(timezone.utc)

    if candidate_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot perform action on yourself.",
        )

    candidate = db.query(User).filter(User.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found.",
        )
    mutual_match = False
    connection_message_saved = False
    ad_due_now = False
    entitlement = _get_or_create_entitlement(db=db, user_id=user.id)
    plan_tier = entitlement.tier
    swipe_allowed = True
    paywall_required = False
    swipes_used: int | None = None
    swipes_remaining: int | None = None

    normalized_connection_message = payload.connection_message.strip() if payload.connection_message else None
    if normalized_connection_message == "":
        normalized_connection_message = None

    if normalized_connection_message and payload.action.value != "like":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="connection_message is only allowed when action is like.",
        )

    if payload.action.value == "unsave":
        request_id = str(payload.request_id) if payload.request_id else str(uuid4())

        db.add(
            SwipeEvent(
                user_id=user.id,
                target_user_id=candidate_id,
                mode=MATCHMAKING_MODE,
                action="unsave",
                is_counted=False,
                counted_swipe_number=None,
                quota_cycle_id=None,
                request_id=request_id,
            )
        )
        (
            db.query(MatchAction)
            .filter(
                MatchAction.actor_user_id == user.id,
                MatchAction.target_user_id == candidate_id,
                MatchAction.action == "save",
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return MatchActionResponse(
            action="unsave",
            mutual_match=False,
            connection_message_saved=False,
            swipe_allowed=True,
            paywall_required=False,
            ad_due_now=False,
            plan_tier=plan_tier,
            swipes_used=None,
            swipes_remaining=None,
        )

    is_counted_action = payload.action.value in COUNTED_ACTIONS
    quota_cycle: SwipeQuotaCycle | None = None
    counted_swipe_number: int | None = None

    if is_counted_action and not entitlement.unlimited_swipes:
        free_swipe_limit = entitlement.matchmaking_swipe_limit or DEFAULT_FREE_SWIPE_LIMIT
        quota_cycle = _get_or_create_quota_cycle(
            db=db,
            user_id=user.id,
            free_swipe_limit=free_swipe_limit,
            now_utc=now_utc,
        )

        if quota_cycle.swipes_used >= quota_cycle.free_swipe_limit:
            swipe_allowed = False
            paywall_required = True
            swipes_used = quota_cycle.swipes_used
            swipes_remaining = 0

            request_id = str(payload.request_id) if payload.request_id else str(uuid4())
            db.add(
                SwipeEvent(
                    user_id=user.id,
                    target_user_id=candidate_id,
                    mode=MATCHMAKING_MODE,
                    action=payload.action.value,
                    is_counted=False,
                    counted_swipe_number=None,
                    quota_cycle_id=quota_cycle.id,
                    request_id=request_id,
                )
            )
            db.commit()

            return MatchActionResponse(
                action=payload.action.value,
                mutual_match=False,
                connection_message_saved=False,
                swipe_allowed=swipe_allowed,
                paywall_required=paywall_required,
                ad_due_now=False,
                plan_tier=plan_tier,
                swipes_used=swipes_used,
                swipes_remaining=swipes_remaining,
            )

        quota_cycle.swipes_used += 1
        counted_swipe_number = quota_cycle.swipes_used
        swipes_used = quota_cycle.swipes_used
        swipes_remaining = max(quota_cycle.free_swipe_limit - quota_cycle.swipes_used, 0)

    match_action = MatchAction(
        actor_user_id=user.id,
        target_user_id=candidate_id,
        action=payload.action.value,
    )
    db.add(match_action)
    db.flush()

    request_id = str(payload.request_id) if payload.request_id else str(uuid4())
    swipe_event = SwipeEvent(
        user_id=user.id,
        target_user_id=candidate_id,
        mode=MATCHMAKING_MODE,
        action=payload.action.value,
        is_counted=bool(is_counted_action and not entitlement.unlimited_swipes),
        counted_swipe_number=counted_swipe_number,
        quota_cycle_id=quota_cycle.id if quota_cycle else None,
        request_id=request_id,
    )
    db.add(swipe_event)
    db.flush()

    if (
        swipe_event.is_counted
        and swipe_event.counted_swipe_number is not None
        and entitlement.ads_enabled
        and swipe_event.counted_swipe_number % AD_EVERY_N_SWIPES == 0
    ):
        ad_due_now = True
        db.add(
            AdTrigger(
                user_id=user.id,
                swipe_event_id=swipe_event.id,
                quota_cycle_id=quota_cycle.id if quota_cycle else None,
                trigger_after_swipe_number=swipe_event.counted_swipe_number,
                ad_placement="matchmaking_interstitial",
                status="pending",
            )
        )

    if payload.action.value == "like" and normalized_connection_message:
        db.add(
            MatchConnectionMessage(
                from_user_id=user.id,
                to_user_id=candidate_id,
                match_action_id=match_action.id,
                message=normalized_connection_message,
            )
        )
        connection_message_saved = True

    if payload.action.value == "like":
        reverse_like = (
            db.query(MatchAction.id)
            .filter(
                MatchAction.actor_user_id == candidate_id,
                MatchAction.target_user_id == user.id,
                MatchAction.action == "like",
            )
            .first()
        )

        match_row: Match | None = None
        if reverse_like is not None:
            mutual_match = True
            user_a_id = min(user.id, candidate_id)
            user_b_id = max(user.id, candidate_id)
            match_row = (
                db.query(Match)
                .filter(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id)
                .first()
            )
            if match_row is None:
                match_row = Match(user_a_id=user_a_id, user_b_id=user_b_id)
                db.add(match_row)
                db.flush()

        now_utc_invite = datetime.now(timezone.utc)
        existing_forward_invite = (
            db.query(Invite)
            .filter(
                Invite.sender_user_id == user.id,
                Invite.recipient_user_id == candidate_id,
                Invite.status == "pending",
            )
            .first()
        )

        if mutual_match and match_row is not None:
            if existing_forward_invite is not None:
                existing_forward_invite.status = "accepted"
                existing_forward_invite.responded_at = now_utc_invite
                existing_forward_invite.mutual_match_id = match_row.id
            else:
                db.add(
                    Invite(
                        public_id=f"inv_{uuid4().hex[:16]}",
                        sender_user_id=user.id,
                        recipient_user_id=candidate_id,
                        source_match_action_id=match_action.id,
                        source_request_id=request_id,
                        status="accepted",
                        message=normalized_connection_message,
                        responded_at=now_utc_invite,
                        mutual_match_id=match_row.id,
                    )
                )

            reverse_invite = (
                db.query(Invite)
                .filter(
                    Invite.sender_user_id == candidate_id,
                    Invite.recipient_user_id == user.id,
                    Invite.status == "pending",
                )
                .first()
            )
            if reverse_invite is not None:
                reverse_invite.status = "accepted"
                reverse_invite.responded_at = now_utc_invite
                reverse_invite.mutual_match_id = match_row.id
                db.add(
                    NotificationOutbox(
                        event_id=str(uuid4()),
                        event_type="invite.accepted",
                        recipient_user_id=candidate_id,
                        invite_id=reverse_invite.id,
                        payload={
                            "type": "invite.accepted",
                            "invite_id": reverse_invite.public_id,
                            "recipient_user_id": candidate_id,
                            "actor_user_id": user.id,
                            "title": "Invite accepted",
                            "body": "Your invitation was accepted!",
                            "deep_link": f"syncfound://invites/sent?invite_id={reverse_invite.public_id}",
                        },
                        status="pending",
                    )
                )
        elif not mutual_match and existing_forward_invite is None:
            forward_invite = Invite(
                public_id=f"inv_{uuid4().hex[:16]}",
                sender_user_id=user.id,
                recipient_user_id=candidate_id,
                source_match_action_id=match_action.id,
                source_request_id=request_id,
                status="pending",
                message=normalized_connection_message,
            )
            db.add(forward_invite)
            db.flush()
            db.add(
                NotificationOutbox(
                    event_id=str(uuid4()),
                    event_type="invite.created",
                    recipient_user_id=candidate_id,
                    invite_id=forward_invite.id,
                    payload={
                        "type": "invite.created",
                        "invite_id": forward_invite.public_id,
                        "recipient_user_id": candidate_id,
                        "sender_user_id": user.id,
                        "title": "New invitation",
                        "body": "Someone invited you to connect",
                        "deep_link": f"syncfound://invites?invite_id={forward_invite.public_id}",
                    },
                    status="pending",
                )
            )

    db.commit()

    return MatchActionResponse(
        action=payload.action.value,
        mutual_match=mutual_match,
        connection_message_saved=connection_message_saved,
        swipe_allowed=swipe_allowed,
        paywall_required=paywall_required,
        ad_due_now=ad_due_now,
        plan_tier=plan_tier,
        swipes_used=swipes_used,
        swipes_remaining=swipes_remaining,
    )


@router.get("/users/me/matches/summary", response_model=MatchSummaryResponse)
def get_match_summary(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    acted_target_subquery = (
        db.query(MatchAction.target_user_id)
        .filter(MatchAction.actor_user_id == user.id)
        .distinct()
        .subquery()
    )

    unseen_candidate_ids = [
        row.user_id
        for row in db.query(UserProfile.user_id)
        .filter(UserProfile.user_id != user.id)
        .filter(~UserProfile.user_id.in_(acted_target_subquery))
        .all()
    ]

    discover_count = len(unseen_candidate_ids)
    matchmaking_count = len(unseen_candidate_ids)

    return MatchSummaryResponse(
        discover_count=discover_count,
        matchmaking_count=matchmaking_count,
        unseen_count=len(unseen_candidate_ids),
    )


@router.get("/users/{candidate_id}/public-profile", response_model=PublicProfileResponse)
def get_public_profile(
    candidate_id: int,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    _get_authenticated_user(authorization=authorization, db=db)

    profile_row = (
        db.query(
            UserProfile.id.label("profile_id"),
            UserProfile.user_id.label("candidate_id"),
            User.full_name.label("display_name"),
            UserProfile.profile_image_uri.label("profile_photo_url"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            UserProfile.title.label("title"),
            UserProfile.bio.label("bio"),
            UserProfile.startup_idea.label("startup_idea"),
            UserProfile.experience_location.label("location_text"),
            UserProfile.linkedin_url.label("linkedin_url"),
            City.city_name.label("city"),
            CountryNew.iso2.label("country_code"),
            CofounderRole.role_name.label("role"),
            MatchingPurpose.matching_purpose.label("intent_badge"),
        )
        .join(User, User.id == UserProfile.user_id)
        .outerjoin(City, City.id == UserProfile.city_id)
        .outerjoin(CountryNew, CountryNew.id == City.country_id)
        .outerjoin(CofounderRole, CofounderRole.id == UserProfile.cofounder_role_id)
        .outerjoin(MatchingPurpose, MatchingPurpose.id == UserProfile.matching_purpose_id)
        .filter(UserProfile.user_id == candidate_id)
        .first()
    )

    if profile_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public profile not found.",
        )

    user_skill_names = [
        row.skill_name
        for row in db.query(UserSkill.skill_name)
        .join(UserProfileUserSkill, UserProfileUserSkill.skill_id == UserSkill.id)
        .filter(UserProfileUserSkill.user_profile_id == profile_row.profile_id)
        .all()
    ]

    cofounder_skill_names = [
        row.skill_name
        for row in db.query(CofounderSkill.skill_name)
        .join(UserProfileCofounderSkill, UserProfileCofounderSkill.skill_id == CofounderSkill.id)
        .filter(UserProfileCofounderSkill.user_profile_id == profile_row.profile_id)
        .all()
    ]

    industry_names = [
        row.industry_name
        for row in db.query(Industry.industry_name)
        .join(UserProfileIndustry, UserProfileIndustry.industry_id == Industry.id)
        .filter(UserProfileIndustry.user_profile_id == profile_row.profile_id)
        .all()
    ]

    return PublicProfileResponse(
        candidate_id=profile_row.candidate_id,
        display_name=profile_row.display_name,
        profile_photo_url=profile_row.profile_photo_url,
        first_name=profile_row.first_name,
        last_name=profile_row.last_name,
        title=profile_row.title,
        bio=profile_row.bio,
        startup_idea=profile_row.startup_idea,
        country_code=profile_row.country_code,
        city=profile_row.city,
        location_text=profile_row.location_text,
        role=profile_row.role,
        intent_badge=profile_row.intent_badge,
        linkedin_url=profile_row.linkedin_url,
        user_skills=user_skill_names,
        cofounder_skills=cofounder_skill_names,
        industries=industry_names,
    )
