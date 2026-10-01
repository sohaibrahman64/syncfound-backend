from fastapi import APIRouter, Depends, Header, HTTPException, status
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.linkedin_profile_model import LinkedInProfile
from app.models.user_model import User
from app.models.user_profile_model import (
    UserProfile,
    UserProfileCofounderSkill,
    UserProfileIndustry,
    UserProfileLocationPreference,
    UserProfileUserSkill,
)
from app.schemas.user_profile_schema import (
    LinkedInProfilePreview,
    UserProfileResponse,
    UserProfileUpsertRequest,
    UserProfileUpsertResponse,
)
from app.services.firebase_service import verify_firebase_id_token


router = APIRouter(prefix="/api/v1", tags=["User Profile"])


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


@router.get("/users/me/profile", response_model=UserProfileResponse)
def get_my_profile(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    location_preferences = (
        db.query(UserProfileLocationPreference)
        .filter(UserProfileLocationPreference.user_profile_id == profile.id)
        .order_by(UserProfileLocationPreference.question_id)
        .all()
    )
    user_skills = (
        db.query(UserProfileUserSkill)
        .filter(UserProfileUserSkill.user_profile_id == profile.id)
        .order_by(UserProfileUserSkill.skill_id)
        .all()
    )
    cofounder_skills = (
        db.query(UserProfileCofounderSkill)
        .filter(UserProfileCofounderSkill.user_profile_id == profile.id)
        .order_by(UserProfileCofounderSkill.skill_id)
        .all()
    )
    industries = (
        db.query(UserProfileIndustry)
        .filter(UserProfileIndustry.user_profile_id == profile.id)
        .order_by(UserProfileIndustry.industry_id)
        .all()
    )

    preview_fields = (
        profile.linkedin_profile_preview_headline,
        profile.linkedin_profile_preview_first_organization,
        profile.linkedin_profile_preview_first_education_institution,
        profile.linkedin_profile_preview_first_location,
        profile.linkedin_profile_preview_connections,
    )
    crop_fields = (
        profile.profile_image_crop_x,
        profile.profile_image_crop_y,
        profile.profile_image_crop_width,
        profile.profile_image_crop_height,
    )

    return UserProfileResponse(
        userId=user.id,
        profileId=profile.id,
        firstName=profile.first_name,
        lastName=profile.last_name,
        dateOfBirth=profile.date_of_birth,
        age=profile.age,
        state=profile.state_id,
        city=profile.city_id,
        locationPreference=[
            {
                "question_id": preference.question_id,
                "selected_answer_id": preference.selected_answer_id,
            }
            for preference in location_preferences
        ],
        matchingPurpose=profile.matching_purpose_id,
        userRole=profile.user_role_id,
        cofounderRole=profile.cofounder_role_id,
        userSkills=[skill.skill_id for skill in user_skills],
        cofounderSkills=[skill.skill_id for skill in cofounder_skills],
        industries=[industry.industry_id for industry in industries],
        title=profile.title,
        primaryRole=profile.primary_role_id,
        secondaryRole=profile.secondary_role_id,
        bio=profile.bio,
        startupIdea=profile.startup_idea,
        fundingStage=profile.funding_stage_id,
        timeCommitment=profile.time_commitment_id,
        riskAppetite=profile.risk_appetite_id,
        employmentType=profile.employment_type_id,
        companyName=profile.company_name,
        experienceLocation=profile.experience_location,
        locationType=profile.location_type_id,
        startDate=profile.start_date,
        currentlyWorkHere=profile.currently_work_here,
        endDate=profile.end_date,
        linkedinUrl=profile.linkedin_url,
        linkedinUsername=profile.linkedin_username,
        linkedinProfilePreview=(
            LinkedInProfilePreview(
                headline=profile.linkedin_profile_preview_headline,
                firstOrganization=profile.linkedin_profile_preview_first_organization,
                firstEducationInstitution=profile.linkedin_profile_preview_first_education_institution,
                firstLocation=profile.linkedin_profile_preview_first_location,
                connections=profile.linkedin_profile_preview_connections,
            )
            if any(value is not None for value in preview_fields)
            else None
        ),
        linkedinProfilePictureUrl=profile.linkedin_profile_picture_url,
        pendingProfileImageUri=profile.pending_profile_image_uri,
        pendingProfileImageSource=profile.pending_profile_image_source,
        profileImageRotation=profile.profile_image_rotation,
        profileImageScale=profile.profile_image_scale,
        profileImageTranslateX=profile.profile_image_translate_x,
        profileImageTranslateY=profile.profile_image_translate_y,
        profileImageCropRect=(
            {
                "x": profile.profile_image_crop_x,
                "y": profile.profile_image_crop_y,
                "width": profile.profile_image_crop_width,
                "height": profile.profile_image_crop_height,
            }
            if all(value is not None for value in crop_fields)
            else None
        ),
        profileImageUri=profile.profile_image_uri,
        profileImageSource=profile.profile_image_source,
    )


@router.patch("/users/me/profile", response_model=UserProfileUpsertResponse)
def upsert_my_profile(
    payload: UserProfileUpsertRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)

    try:
        linkedin_profile = (
            db.query(LinkedInProfile)
            .filter(LinkedInProfile.user_id == user.id)
            .first()
        )

        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if profile is None:
            profile = UserProfile(user_id=user.id)
            db.add(profile)

        profile.first_name = payload.firstName
        profile.last_name = payload.lastName
        profile.date_of_birth = payload.dateOfBirth
        profile.age = payload.age
        profile.state_id = payload.state
        profile.city_id = payload.city
        profile.matching_purpose_id = payload.matchingPurpose
        profile.user_role_id = payload.userRole
        profile.cofounder_role_id = payload.cofounderRole
        profile.title = payload.title
        profile.primary_role_id = payload.primaryRole
        profile.secondary_role_id = payload.secondaryRole
        profile.bio = payload.bio
        profile.startup_idea = payload.startupIdea
        profile.funding_stage_id = payload.fundingStage
        profile.time_commitment_id = payload.timeCommitment
        profile.risk_appetite_id = payload.riskAppetite
        profile.employment_type_id = payload.employmentType
        profile.company_name = payload.companyName
        profile.experience_location = payload.experienceLocation
        profile.location_type_id = payload.locationType
        profile.start_date = payload.startDate
        profile.currently_work_here = payload.currentlyWorkHere
        profile.end_date = payload.endDate
        profile.linkedin_url = payload.linkedinUrl
        profile.linkedin_username = payload.linkedinUsername
        profile.linkedin_profile_picture_url = payload.linkedinProfilePictureUrl
        profile.pending_profile_image_uri = payload.pendingProfileImageUri
        profile.pending_profile_image_source = payload.pendingProfileImageSource
        profile.profile_image_rotation = payload.profileImageRotation
        profile.profile_image_scale = payload.profileImageScale
        profile.profile_image_translate_x = payload.profileImageTranslateX
        profile.profile_image_translate_y = payload.profileImageTranslateY
        profile.profile_image_uri = payload.profileImageUri
        profile.profile_image_source = payload.profileImageSource
        profile.linkedin_profile_id = linkedin_profile.id if linkedin_profile else None

        if payload.linkedinProfilePreview is not None:
            profile.linkedin_profile_preview_headline = payload.linkedinProfilePreview.headline
            profile.linkedin_profile_preview_first_organization = payload.linkedinProfilePreview.firstOrganization
            profile.linkedin_profile_preview_first_education_institution = payload.linkedinProfilePreview.firstEducationInstitution
            profile.linkedin_profile_preview_first_location = payload.linkedinProfilePreview.firstLocation
            profile.linkedin_profile_preview_connections = payload.linkedinProfilePreview.connections
        else:
            profile.linkedin_profile_preview_headline = None
            profile.linkedin_profile_preview_first_organization = None
            profile.linkedin_profile_preview_first_education_institution = None
            profile.linkedin_profile_preview_first_location = None
            profile.linkedin_profile_preview_connections = None

        if payload.profileImageCropRect is not None:
            profile.profile_image_crop_x = payload.profileImageCropRect.x
            profile.profile_image_crop_y = payload.profileImageCropRect.y
            profile.profile_image_crop_width = payload.profileImageCropRect.width
            profile.profile_image_crop_height = payload.profileImageCropRect.height
        else:
            profile.profile_image_crop_x = None
            profile.profile_image_crop_y = None
            profile.profile_image_crop_width = None
            profile.profile_image_crop_height = None

        db.flush()

        db.query(UserProfileLocationPreference).filter(
            UserProfileLocationPreference.user_profile_id == profile.id
        ).delete(synchronize_session=False)
        db.query(UserProfileUserSkill).filter(
            UserProfileUserSkill.user_profile_id == profile.id
        ).delete(synchronize_session=False)
        db.query(UserProfileCofounderSkill).filter(
            UserProfileCofounderSkill.user_profile_id == profile.id
        ).delete(synchronize_session=False)
        db.query(UserProfileIndustry).filter(
            UserProfileIndustry.user_profile_id == profile.id
        ).delete(synchronize_session=False)

        for location_preference in payload.locationPreference:
            db.add(
                UserProfileLocationPreference(
                    user_profile_id=profile.id,
                    question_id=location_preference.question_id,
                    selected_answer_id=location_preference.selected_answer_id,
                )
            )

        for skill_id in payload.userSkills:
            db.add(
                UserProfileUserSkill(
                    user_profile_id=profile.id,
                    skill_id=skill_id,
                )
            )

        for skill_id in payload.cofounderSkills:
            db.add(
                UserProfileCofounderSkill(
                    user_profile_id=profile.id,
                    skill_id=skill_id,
                )
            )

        for industry_id in payload.industries:
            db.add(
                UserProfileIndustry(
                    user_profile_id=profile.id,
                    industry_id=industry_id,
                )
            )

        db.commit()
        db.refresh(profile)

        return UserProfileUpsertResponse(
            message="User profile updated successfully.",
            user_id=user.id,
            profile_id=profile.id,
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid foreign key reference in request payload.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert user profile: {str(exc)}",
        ) from exc