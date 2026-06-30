from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.city_model import City
from app.models.cofounder_role_model import CofounderRole
from app.models.cofounder_skill_model import CofounderSkill
from app.models.country_new_model import CountryNew
from app.models.industry_model import Industry
from app.models.invite_model import Invite
from app.models.linkedin_profile_model import LinkedInProfile, LinkedInProfileExperience
from app.models.linkedin_profile_model import LinkedInProfileEducation
from app.models.match_model import Match, MatchAction
from app.models.notification_outbox_model import NotificationOutbox
from app.models.matching_purpose_model import MatchingPurpose
from app.models.time_commitment_model import TimeCommitment
from app.models.user_model import User
from app.models.user_profile_model import UserProfile, UserProfileCofounderSkill, UserProfileIndustry, UserProfileUserSkill
from app.models.user_role_model import UserRole
from app.models.user_skill_model import UserSkill
from app.schemas.invites_schema import (
    InviteCountsResponse,
    InviteItem,
    InviteEducationResponse,
    InviteLinkedInExperienceResponse,
    InviteUserDetailsResponse,
    InviteMutateRequest,
    InviteMutateResponse,
    InviteProfileCard,
    InviteWithdrawRequest,
    InviteWithdrawResponse,
    PassedEntry,
    PassedListResponse,
    ReceivedInviteEntry,
    ReceivedInviteListResponse,
    SavedEntry,
    SavedListResponse,
    SentInviteEntry,
    SentInviteListResponse,
    VALID_MUTATE_ACTIONS,
)
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["Invites"])

_INVITE_STATUSES = {"pending", "accepted", "declined", "withdrawn", "expired", "all"}
_TERMINAL_STATUSES = {"accepted", "declined", "withdrawn", "expired"}


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return user


def _build_list_cursor(created_at: datetime, row_id: int) -> str:
    payload = {"created_at": created_at.isoformat(), "id": row_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _parse_list_cursor(cursor: str | None) -> tuple[datetime, int] | None:
    if not cursor:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
        return datetime.fromisoformat(data["created_at"]), int(data["id"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor.") from exc


def _build_profile_cards(user_ids: list[int], db: Session) -> dict[int, InviteProfileCard]:
    if not user_ids:
        return {}

    rows = (
        db.query(
            UserProfile.user_id.label("uid"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            UserProfile.profile_image_uri.label("photo"),
            City.city_name.label("city"),
            CountryNew.iso2.label("country_code"),
            MatchingPurpose.matching_purpose.label("intent_badge"),
            TimeCommitment.time_commitment_name.label("time_commitment"),
            UserProfile.id.label("profile_id"),
        )
        .outerjoin(City, City.id == UserProfile.city_id)
        .outerjoin(CountryNew, CountryNew.id == City.country_id)
        .outerjoin(MatchingPurpose, MatchingPurpose.id == UserProfile.matching_purpose_id)
        .outerjoin(TimeCommitment, TimeCommitment.id == UserProfile.time_commitment_id)
        .filter(UserProfile.user_id.in_(user_ids))
        .all()
    )

    profile_ids = [row.profile_id for row in rows]
    skill_rows = (
        db.query(UserProfileCofounderSkill.user_profile_id, CofounderSkill.skill_name)
        .join(CofounderSkill, CofounderSkill.id == UserProfileCofounderSkill.skill_id)
        .filter(UserProfileCofounderSkill.user_profile_id.in_(profile_ids))
        .all()
    ) if profile_ids else []

    skills_by_profile: dict[int, list[str]] = {}
    for profile_id, skill_name in skill_rows:
        skills_by_profile.setdefault(profile_id, []).append(skill_name)

    cards: dict[int, InviteProfileCard] = {}
    for row in rows:
        display_name = " ".join(part for part in [row.first_name, row.last_name] if part).strip() or None
        location_parts = [part for part in [row.city, row.country_code] if part]
        cards[row.uid] = InviteProfileCard(
            user_id=row.uid,
            display_name=display_name,
            profile_photo_url=row.photo,
            location_text=", ".join(location_parts) if location_parts else None,
            intent_badge=row.intent_badge,
            time_commitment=row.time_commitment,
            role_tags=skills_by_profile.get(row.profile_id, []),
        )
    return cards


def _empty_card(user_id: int) -> InviteProfileCard:
    return InviteProfileCard(user_id=user_id)


def _actor_card(user_id: int, db: Session) -> InviteProfileCard:
    cards = _build_profile_cards([user_id], db)
    return cards.get(user_id, _empty_card(user_id))


def _build_profile_details(user_ids: list[int], db: Session) -> dict[int, InviteUserDetailsResponse]:
    if not user_ids:
        return {}

    rows = (
        db.query(
            UserProfile.user_id.label("uid"),
            UserProfile.id.label("profile_id"),
            UserProfile.age.label("age"),
            UserProfile.first_name.label("first_name"),
            UserProfile.last_name.label("last_name"),
            UserProfile.title.label("title"),
            UserProfile.profile_image_uri.label("profile_photo_url"),
            CountryNew.iso2.label("country_code"),
            City.city_name.label("city"),
            UserProfile.experience_location.label("location_text"),
            UserRole.role_name.label("user_role"),
            CofounderRole.role_name.label("role"),
            MatchingPurpose.matching_purpose.label("intent_badge"),
            UserProfile.bio.label("bio"),
            UserProfile.startup_idea.label("startup_idea"),
            UserProfile.linkedin_url.label("linkedin_url"),
            UserProfile.linkedin_profile_id.label("linkedin_profile_id"),
        )
        .outerjoin(City, City.id == UserProfile.city_id)
        .outerjoin(CountryNew, CountryNew.id == City.country_id)
        .outerjoin(UserRole, UserRole.id == UserProfile.user_role_id)
        .outerjoin(CofounderRole, CofounderRole.id == UserProfile.cofounder_role_id)
        .outerjoin(MatchingPurpose, MatchingPurpose.id == UserProfile.matching_purpose_id)
        .filter(UserProfile.user_id.in_(user_ids))
        .all()
    )

    profile_ids = [row.profile_id for row in rows]
    user_skill_names_map: dict[int, list[str]] = {}
    cofounder_skill_names_map: dict[int, list[str]] = {}
    industry_names_map: dict[int, list[str]] = {}

    if profile_ids:
        user_skill_rows = (
            db.query(UserProfileUserSkill.user_profile_id, UserSkill.skill_name)
            .join(UserSkill, UserSkill.id == UserProfileUserSkill.skill_id)
            .filter(UserProfileUserSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_name in user_skill_rows:
            user_skill_names_map.setdefault(profile_id, []).append(skill_name)

        cofounder_skill_rows = (
            db.query(UserProfileCofounderSkill.user_profile_id, CofounderSkill.skill_name)
            .join(CofounderSkill, CofounderSkill.id == UserProfileCofounderSkill.skill_id)
            .filter(UserProfileCofounderSkill.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, skill_name in cofounder_skill_rows:
            cofounder_skill_names_map.setdefault(profile_id, []).append(skill_name)

        industry_rows = (
            db.query(UserProfileIndustry.user_profile_id, Industry.industry_name)
            .join(Industry, Industry.id == UserProfileIndustry.industry_id)
            .filter(UserProfileIndustry.user_profile_id.in_(profile_ids))
            .all()
        )
        for profile_id, industry_name in industry_rows:
            industry_names_map.setdefault(profile_id, []).append(industry_name)

    linkedin_profile_ids = [row.linkedin_profile_id for row in rows if row.linkedin_profile_id is not None]
    linkedin_summary_map: dict[int, dict[str, str | None]] = {}
    linkedin_experiences_map: dict[int, list[InviteLinkedInExperienceResponse]] = {}
    linkedin_education_map: dict[int, list[InviteEducationResponse]] = {}

    if linkedin_profile_ids:
        linkedin_rows = (
            db.query(
                LinkedInProfile.id.label("linkedin_profile_id"),
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

        profile_by_linkedin_id = {
            row.linkedin_profile_id: row.profile_id
            for row in rows
            if row.linkedin_profile_id is not None
        }

        for row in linkedin_rows:
            profile_id = profile_by_linkedin_id.get(row.linkedin_profile_id)
            if profile_id is None:
                continue
            linkedin_summary_map[profile_id] = {
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
            profile_id = profile_by_linkedin_id.get(row.profile_id)
            if profile_id is None:
                continue
            linkedin_experiences_map.setdefault(profile_id, []).append(
                InviteLinkedInExperienceResponse(
                    title=row.title,
                    company=row.company,
                    location=row.location,
                    description=row.description,
                    duration=row.duration,
                    start_year=row.start_year,
                    start_month=row.start_month,
                    end_year=row.end_year,
                    end_month=row.end_month,
                    is_current=row.is_current,
                    company_linkedin_url=row.company_linkedin_url,
                    company_logo_url=row.company_logo_url,
                    employment_type=row.employment_type,
                    location_type=row.location_type,
                )
            )

        linkedin_education_rows = (
            db.query(
                LinkedInProfileEducation.profile_id.label("profile_id"),
                LinkedInProfileEducation.school.label("school"),
                LinkedInProfileEducation.degree.label("degree"),
                LinkedInProfileEducation.degree_name.label("degree_name"),
                LinkedInProfileEducation.field_of_study.label("field_of_study"),
                LinkedInProfileEducation.duration.label("duration"),
                LinkedInProfileEducation.school_linkedin_url.label("school_linkedin_url"),
                LinkedInProfileEducation.start_year.label("start_year"),
                LinkedInProfileEducation.start_month.label("start_month"),
                LinkedInProfileEducation.end_year.label("end_year"),
                LinkedInProfileEducation.end_month.label("end_month"),
            )
            .filter(LinkedInProfileEducation.profile_id.in_(linkedin_profile_ids))
            .order_by(LinkedInProfileEducation.id.asc())
            .all()
        )
        for row in linkedin_education_rows:
            profile_id = profile_by_linkedin_id.get(row.profile_id)
            if profile_id is None:
                continue
            linkedin_education_map.setdefault(profile_id, []).append(
                InviteEducationResponse(
                    school=row.school,
                    degree=row.degree,
                    degree_name=row.degree_name,
                    field_of_study=row.field_of_study,
                    duration=row.duration,
                    school_linkedin_url=row.school_linkedin_url,
                    start_year=row.start_year,
                    start_month=row.start_month,
                    end_year=row.end_year,
                    end_month=row.end_month,
                )
            )

    details_map: dict[int, InviteUserDetailsResponse] = {}
    for row in rows:
        display_name = " ".join(part for part in [row.first_name, row.last_name] if part).strip() or None
        summary = linkedin_summary_map.get(row.profile_id, {})
        details_map[row.uid] = InviteUserDetailsResponse(
            user_id=row.uid,
            display_name=display_name,
            first_name=row.first_name,
            last_name=row.last_name,
            age=row.age,
            title=row.title,
            profile_photo_url=row.profile_photo_url,
            country_code=row.country_code,
            city=row.city,
            location_text=row.location_text,
            user_role=row.user_role,
            role=row.role,
            intent_badge=row.intent_badge,
            bio=row.bio,
            experience_summary=row.bio,
            startup_idea=row.startup_idea,
            linkedin_url=row.linkedin_url,
            user_skills=user_skill_names_map.get(row.profile_id, []),
            cofounder_skills=cofounder_skill_names_map.get(row.profile_id, []),
            industries=industry_names_map.get(row.profile_id, []),
            linkedin_headline=summary.get("headline"),
            linkedin_current_company=summary.get("current_company"),
            linkedin_location=summary.get("location"),
            linkedin_top_education_school_name=summary.get("top_education_school_name"),
            linkedin_experiences=linkedin_experiences_map.get(row.profile_id, []),
            education_details=linkedin_education_map.get(row.profile_id, []),
        )

    return details_map


@router.get("/users/me/invites", response_model=ReceivedInviteListResponse)
def get_received_invites(
    filter_status: str = Query(default="pending", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    if filter_status not in _INVITE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status.")

    query = db.query(Invite).filter(Invite.recipient_user_id == user.id)
    if filter_status != "all":
        query = query.filter(Invite.status == filter_status)

    cursor_tuple = _parse_list_cursor(cursor)
    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        query = query.filter((Invite.created_at < cursor_dt) | ((Invite.created_at == cursor_dt) & (Invite.id < cursor_id)))

    rows = query.order_by(Invite.created_at.desc(), Invite.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    source_details_map = _build_profile_details([row.sender_user_id for row in rows], db)
    cards = _build_profile_cards([row.sender_user_id for row in rows], db)

    items = [
        ReceivedInviteEntry(
            invite=InviteItem(
                invite_id=row.public_id,
                status=row.status,
                message=row.message,
                created_at=row.created_at,
                updated_at=row.updated_at,
                read_at=row.read_at,
                responded_at=row.responded_at,
            ),
            performed_by_profile=cards.get(row.sender_user_id, _empty_card(row.sender_user_id)),
            from_profile=cards.get(row.sender_user_id, _empty_card(row.sender_user_id)),
            source_profile_details=source_details_map.get(row.sender_user_id),
        )
        for row in rows
    ]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _build_list_cursor(last.created_at, last.id)

    return ReceivedInviteListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/users/me/invites/sent", response_model=SentInviteListResponse)
def get_sent_invites(
    filter_status: str = Query(default="all", alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    if filter_status not in _INVITE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status.")

    query = db.query(Invite).filter(Invite.sender_user_id == user.id)
    if filter_status != "all":
        query = query.filter(Invite.status == filter_status)

    cursor_tuple = _parse_list_cursor(cursor)
    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        query = query.filter((Invite.created_at < cursor_dt) | ((Invite.created_at == cursor_dt) & (Invite.id < cursor_id)))

    rows = query.order_by(Invite.created_at.desc(), Invite.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    actor = _actor_card(user.id, db)
    target_details_map = _build_profile_details([row.recipient_user_id for row in rows], db)
    cards = _build_profile_cards([row.recipient_user_id for row in rows], db)

    items = [
        SentInviteEntry(
            invite=InviteItem(
                invite_id=row.public_id,
                status=row.status,
                message=row.message,
                created_at=row.created_at,
                updated_at=row.updated_at,
                read_at=row.read_at,
                responded_at=row.responded_at,
            ),
            performed_by_profile=actor,
            to_profile=cards.get(row.recipient_user_id, _empty_card(row.recipient_user_id)),
            target_profile_details=target_details_map.get(row.recipient_user_id),
        )
        for row in rows
    ]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _build_list_cursor(last.created_at, last.id)

    return SentInviteListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/users/me/saved", response_model=SavedListResponse)
def get_saved_profiles(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    query = db.query(MatchAction).filter(MatchAction.actor_user_id == user.id, MatchAction.action == "save")

    cursor_tuple = _parse_list_cursor(cursor)
    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        query = query.filter((MatchAction.created_at < cursor_dt) | ((MatchAction.created_at == cursor_dt) & (MatchAction.id < cursor_id)))

    rows = query.order_by(MatchAction.created_at.desc(), MatchAction.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    actor = _actor_card(user.id, db)
    target_details_map = _build_profile_details([row.target_user_id for row in rows], db)
    cards = _build_profile_cards([row.target_user_id for row in rows], db)
    items = [
        SavedEntry(
            saved_id=row.id,
            saved_at=row.created_at,
            performed_by_profile=actor,
            profile=cards.get(row.target_user_id, _empty_card(row.target_user_id)),
            target_profile_details=target_details_map.get(row.target_user_id),
        )
        for row in rows
    ]

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _build_list_cursor(last.created_at, last.id)

    return SavedListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/users/me/passed", response_model=PassedListResponse)
def get_passed_profiles(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    cursor_tuple = _parse_list_cursor(cursor)

    pass_query = db.query(
        MatchAction.id.label("event_id"),
        MatchAction.created_at.label("event_at"),
        MatchAction.target_user_id.label("target_user_id"),
    ).filter(
        MatchAction.actor_user_id == user.id,
        MatchAction.action == "pass",
    )

    declined_event_at = func.coalesce(Invite.responded_at, Invite.updated_at, Invite.created_at)
    declined_query = db.query(
        Invite.id.label("event_id"),
        declined_event_at.label("event_at"),
        Invite.sender_user_id.label("target_user_id"),
    ).filter(
        Invite.recipient_user_id == user.id,
        Invite.status == "declined",
    )

    if cursor_tuple is not None:
        cursor_dt, cursor_id = cursor_tuple
        pass_query = pass_query.filter(
            (MatchAction.created_at < cursor_dt)
            | ((MatchAction.created_at == cursor_dt) & (MatchAction.id < cursor_id))
        )
        declined_query = declined_query.filter(
            (declined_event_at < cursor_dt)
            | ((declined_event_at == cursor_dt) & (Invite.id < cursor_id))
        )

    pass_rows = pass_query.order_by(MatchAction.created_at.desc(), MatchAction.id.desc()).limit(limit + 1).all()
    declined_rows = declined_query.order_by(declined_event_at.desc(), Invite.id.desc()).limit(limit + 1).all()

    merged_events = [
        {
            "event_id": row.event_id,
            "event_at": row.event_at,
            "target_user_id": row.target_user_id,
        }
        for row in pass_rows
    ] + [
        {
            "event_id": row.event_id,
            "event_at": row.event_at,
            "target_user_id": row.target_user_id,
        }
        for row in declined_rows
    ]

    merged_events.sort(key=lambda item: (item["event_at"], item["event_id"]), reverse=True)
    has_more = len(merged_events) > limit
    merged_events = merged_events[:limit]

    actor = _actor_card(user.id, db)
    target_user_ids = [item["target_user_id"] for item in merged_events]
    target_details_map = _build_profile_details(target_user_ids, db)
    cards = _build_profile_cards(target_user_ids, db)

    items = [
        PassedEntry(
            passed_id=item["event_id"],
            passed_at=item["event_at"],
            performed_by_profile=actor,
            profile=cards.get(item["target_user_id"], _empty_card(item["target_user_id"])),
            target_profile_details=target_details_map.get(item["target_user_id"]),
        )
        for item in merged_events
    ]

    next_cursor = None
    if has_more and merged_events:
        last = merged_events[-1]
        next_cursor = _build_list_cursor(last["event_at"], last["event_id"])

    return PassedListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/users/me/invites/counts", response_model=InviteCountsResponse)
def get_invite_counts(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    invite_rows = (
        db.query(
            func.count().filter(Invite.status == "pending").label("pending"),
            func.count().filter(Invite.status == "pending", Invite.read_at.is_(None)).label("unread"),
        )
        .filter(Invite.recipient_user_id == user.id)
        .one()
    )

    sent_pending = db.query(func.count(Invite.id)).filter(Invite.sender_user_id == user.id, Invite.status == "pending").scalar() or 0
    saved_total = db.query(func.count(MatchAction.id)).filter(MatchAction.actor_user_id == user.id, MatchAction.action == "save").scalar() or 0
    passed_total = db.query(func.count(MatchAction.id)).filter(MatchAction.actor_user_id == user.id, MatchAction.action == "pass").scalar() or 0

    return InviteCountsResponse(
        invites_pending=invite_rows.pending or 0,
        invites_unread=invite_rows.unread or 0,
        sent_pending=sent_pending,
        saved_total=saved_total,
        passed_total=passed_total,
    )


@router.patch("/users/me/invites/{public_id}", response_model=InviteMutateResponse)
def mutate_invite(
    public_id: str,
    payload: InviteMutateRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    if payload.action not in VALID_MUTATE_ACTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action.")

    invite = db.query(Invite).filter(Invite.public_id == public_id).first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")

    if invite.recipient_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    now_utc = datetime.now(timezone.utc)
    mutual_match = False
    match_id: int | None = None

    if payload.action == "mark_read":
        if invite.read_at is None:
            invite.read_at = now_utc
            invite.updated_at = now_utc
            db.commit()
            db.refresh(invite)
        return InviteMutateResponse(
            invite_id=invite.public_id,
            status=invite.status,
            updated_at=invite.updated_at,
            mutual_match=False,
            match_id=None,
        )

    if invite.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid transition.")

    if payload.action == "accept":
        invite.status = "accepted"
        invite.responded_at = now_utc
        invite.updated_at = now_utc

        user_a_id = min(invite.sender_user_id, invite.recipient_user_id)
        user_b_id = max(invite.sender_user_id, invite.recipient_user_id)
        match_row = db.query(Match).filter(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id).first()
        if match_row is None:
            match_row = Match(user_a_id=user_a_id, user_b_id=user_b_id)
            db.add(match_row)
            db.flush()
        invite.mutual_match_id = match_row.id
        mutual_match = True
        match_id = match_row.id

        db.add(
            NotificationOutbox(
                event_id=str(uuid4()),
                event_type="invite.accepted",
                recipient_user_id=invite.sender_user_id,
                invite_id=invite.id,
                payload={
                    "type": "invite.accepted",
                    "invite_id": invite.public_id,
                    "recipient_user_id": invite.sender_user_id,
                    "actor_user_id": invite.recipient_user_id,
                    "title": "Invite accepted",
                    "body": "Your invitation was accepted!",
                    "deep_link": f"syncfound://invites/sent?invite_id={invite.public_id}",
                },
                status="pending",
            )
        )

    elif payload.action == "decline":
        invite.status = "declined"
        invite.responded_at = now_utc
        invite.updated_at = now_utc
        db.add(
            NotificationOutbox(
                event_id=str(uuid4()),
                event_type="invite.declined",
                recipient_user_id=invite.sender_user_id,
                invite_id=invite.id,
                payload={
                    "type": "invite.declined",
                    "invite_id": invite.public_id,
                    "recipient_user_id": invite.sender_user_id,
                    "actor_user_id": invite.recipient_user_id,
                    "title": "Invite declined",
                    "body": "Your invitation was declined.",
                    "deep_link": f"syncfound://invites/sent?invite_id={invite.public_id}",
                },
                status="pending",
            )
        )

    db.commit()
    db.refresh(invite)
    return InviteMutateResponse(
        invite_id=invite.public_id,
        status=invite.status,
        updated_at=invite.updated_at,
        mutual_match=mutual_match,
        match_id=match_id,
    )


@router.post("/users/me/invites/{public_id}/withdraw", response_model=InviteWithdrawResponse)
def withdraw_invite(
    public_id: str,
    payload: InviteWithdrawRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    invite = db.query(Invite).filter(Invite.public_id == public_id).first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")

    if invite.sender_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    if invite.status in _TERMINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite is already finalized.")

    now_utc = datetime.now(timezone.utc)
    invite.status = "withdrawn"
    invite.withdrawn_at = now_utc
    invite.responded_at = now_utc
    invite.updated_at = now_utc

    db.add(
        NotificationOutbox(
            event_id=str(uuid4()),
            event_type="invite.withdrawn",
            recipient_user_id=invite.recipient_user_id,
            invite_id=invite.id,
            payload={
                "type": "invite.withdrawn",
                "invite_id": invite.public_id,
                "recipient_user_id": invite.recipient_user_id,
                "actor_user_id": invite.sender_user_id,
                "title": "Invite withdrawn",
                "body": "An invitation was withdrawn.",
                "deep_link": f"syncfound://invites?invite_id={invite.public_id}",
            },
            status="pending",
        )
    )

    db.commit()
    db.refresh(invite)
    return InviteWithdrawResponse(
        invite_id=invite.public_id,
        status=invite.status,
        updated_at=invite.updated_at,
    )
