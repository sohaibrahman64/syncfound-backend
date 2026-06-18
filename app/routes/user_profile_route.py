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
from app.schemas.user_profile_schema import UserProfileUpsertRequest, UserProfileUpsertResponse
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