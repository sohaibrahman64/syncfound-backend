from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.linkedin_profile_model import (
    LinkedInProfile,
    LinkedInProfileCause,
    LinkedInProfileCertification,
    LinkedInProfileCourse,
    LinkedInProfileCreatorHashtag,
    LinkedInProfileEducation,
    LinkedInProfileExperience,
    LinkedInProfileExperienceSkill,
    LinkedInProfileLanguage,
    LinkedInProfileProject,
    LinkedInProfileTopSkill,
)
from app.models.user_model import User
from app.schemas.linkedin_profile_schema import (
    LinkedInProfileIngestRequest,
    LinkedInProfileIngestResponse,
)
from app.services.apify_service import fetch_linkedin_profile as fetch_linkedin_profile_from_apify

router = APIRouter(prefix="/api/v1", tags=["LinkedIn Profile"])

@router.get("/linkedin-profile", summary="Fetch LinkedIn profile data by username")
def fetch_linkedin_profile_data(username: str) -> dict:

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username query parameter is required.",
        )
    try:
        profile_data = fetch_linkedin_profile_from_apify(username)
        return profile_data.json() if hasattr(profile_data, "json") else profile_data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch LinkedIn profile data: {str(exc)}",
        ) from exc


@router.post(
    "/linkedin-profile/ingest",
    response_model=LinkedInProfileIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store LinkedIn profile details",
)
def ingest_linkedin_profile_data(
    payload: LinkedInProfileIngestRequest,
    db: Session = Depends(get_db),
) -> LinkedInProfileIngestResponse:
    user = db.query(User).filter(User.id == payload.userid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    try:
        existing_profile = (
            db.query(LinkedInProfile)
            .filter(LinkedInProfile.user_id == payload.userid)
            .first()
        )
        if existing_profile is not None:
            db.delete(existing_profile)
            db.flush()

        basic_info = payload.basic_info
        location = basic_info.location
        top_education_school = basic_info.top_education_school

        profile = LinkedInProfile(
            user_id=payload.userid,
            fullname=basic_info.fullname,
            first_name=basic_info.first_name,
            last_name=basic_info.last_name,
            headline=basic_info.headline,
            public_identifier=basic_info.public_identifier,
            profile_url=basic_info.profile_url,
            profile_picture_url=basic_info.profile_picture_url,
            about=basic_info.about,
            location_country=location.country if location else None,
            location_city=location.city if location else None,
            location_full=location.full if location else None,
            location_postal_code=location.postal_code if location else None,
            location_country_code=location.country_code if location else None,
            is_creator=basic_info.is_creator,
            is_influencer=basic_info.is_influencer,
            is_premium=basic_info.is_premium,
            open_to_work=basic_info.open_to_work,
            created_timestamp_ms=basic_info.created_timestamp,
            show_follower_count=basic_info.show_follower_count,
            background_picture_url=basic_info.background_picture_url,
            memorialized=basic_info.memorialized,
            is_top_voice=basic_info.is_top_voice,
            primary_locale=basic_info.primary_locale,
            urn=basic_info.urn,
            follower_count=basic_info.follower_count,
            connection_count=basic_info.connection_count,
            top_education_school_name=top_education_school.name if top_education_school else None,
            top_education_school_urn=top_education_school.urn if top_education_school else None,
            top_education_school_url=top_education_school.url if top_education_school else None,
            top_education_school_logo_url=top_education_school.logo_url if top_education_school else None,
            current_company=basic_info.current_company,
            current_company_urn=basic_info.current_company_urn,
            email=basic_info.email,
        )
        db.add(profile)
        db.flush()

        for hashtag in basic_info.creator_hashtags:
            db.add(
                LinkedInProfileCreatorHashtag(
                    profile_id=profile.id,
                    hashtag=hashtag,
                )
            )

        for skill in basic_info.top_skills:
            db.add(
                LinkedInProfileTopSkill(
                    profile_id=profile.id,
                    skill=skill,
                )
            )

        for experience_item in payload.experience:
            experience = LinkedInProfileExperience(
                profile_id=profile.id,
                title=experience_item.title,
                company=experience_item.company,
                location=experience_item.location,
                description=experience_item.description,
                duration=experience_item.duration,
                start_year=experience_item.start_date.year if experience_item.start_date else None,
                start_month=experience_item.start_date.month if experience_item.start_date else None,
                end_year=experience_item.end_date.year if experience_item.end_date else None,
                end_month=experience_item.end_date.month if experience_item.end_date else None,
                is_current=experience_item.is_current,
                company_linkedin_url=experience_item.company_linkedin_url,
                company_logo_url=experience_item.company_logo_url,
                employment_type=experience_item.employment_type,
                location_type=experience_item.location_type,
                company_id=experience_item.company_id,
                skills_url=experience_item.skills_url,
            )
            db.add(experience)
            db.flush()

            for skill in experience_item.skills:
                db.add(
                    LinkedInProfileExperienceSkill(
                        experience_id=experience.id,
                        skill=skill,
                    )
                )

        for education_item in payload.education:
            db.add(
                LinkedInProfileEducation(
                    profile_id=profile.id,
                    school=education_item.school,
                    degree=education_item.degree,
                    degree_name=education_item.degree_name,
                    field_of_study=education_item.field_of_study,
                    duration=education_item.duration,
                    school_linkedin_url=education_item.school_linkedin_url,
                    start_year=education_item.start_date.year if education_item.start_date else None,
                    start_month=education_item.start_date.month if education_item.start_date else None,
                    end_year=education_item.end_date.year if education_item.end_date else None,
                    end_month=education_item.end_date.month if education_item.end_date else None,
                )
            )

        for project_item in payload.projects:
            db.add(
                LinkedInProfileProject(
                    profile_id=profile.id,
                    name=project_item.name,
                    description=project_item.description,
                    is_current=project_item.is_current,
                )
            )

        for certification_item in payload.certifications:
            db.add(
                LinkedInProfileCertification(
                    profile_id=profile.id,
                    name=certification_item.name,
                    issuer=certification_item.issuer,
                    issued_date=certification_item.issued_date,
                )
            )

        for language_item in payload.languages:
            db.add(
                LinkedInProfileLanguage(
                    profile_id=profile.id,
                    language=language_item.language,
                    proficiency=language_item.proficiency,
                )
            )

        for course_item in payload.courses:
            db.add(
                LinkedInProfileCourse(
                    profile_id=profile.id,
                    title=course_item.title,
                )
            )

        for cause_item in payload.causes:
            db.add(
                LinkedInProfileCause(
                    profile_id=profile.id,
                    cause=cause_item,
                )
            )

        db.commit()

        return LinkedInProfileIngestResponse(
            message="LinkedIn profile stored successfully.",
            profile_id=profile.id,
            user_id=payload.userid,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store LinkedIn profile data: {str(exc)}",
        ) from exc
