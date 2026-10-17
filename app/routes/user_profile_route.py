from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.models.user_skill_model import UserSkill
from app.schemas.user_skill_schema import UserSkillResponse
from firebase_admin import exceptions as firebase_exceptions
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.linkedin_profile_model import (
    LinkedInProfile,
    LinkedInProfileExperience,
    LinkedInProfileEducation,
)
from app.models.industry_model import Industry
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
from app.schemas.industry_schema import IndustryResponse
from app.schemas.linkedin_profile_schema import LinkedInProfileDetailsResponse
from app.services.firebase_service import verify_firebase_id_token
from app.schemas.user_profile_schema import LocationPreferenceQuestionResponse, LocationPreferenceAnswerResponse
from app.models.location_preference_model import LocationPreferenceQuestion, LocationPreferenceAnswer
from app.models.country_new_model import CountryNew
from app.models.state_model import State
from app.models.city_model import City
from app.schemas.user_profile_schema import LocationDetailsResponse
from app.models.location_preference_model import (
    LocationPreferenceAnswer,
)
from app.models.user_profile_experiences_model import UserProfileExperience
from app.models.user_profile_education_model import UserProfileEducation
from app.models.user_company_size_interests_model import UserCompanySizeInterest
from app.models.user_profile_compensation_model import UserProfileCompensation
from app.models.user_job_search_profile_model import UserJobSearchProfile
from app.models.user_job_search_profile_work_types_model import (
    UserJobSearchProfileWorkType,
)
from app.models.user_profile_prompts_model import UserProfilePrompt
from app.schemas.user_profile_experience_schema import (
    UserProfileExperienceResponse,
)

from app.schemas.user_profile_education_schema import (
    UserProfileEducationResponse,
)

from app.schemas.user_company_size_interest_schema import (
    UserCompanySizeInterestResponse,
)

from app.schemas.user_profile_compensation_schema import (
    UserProfileCompensationResponse,
)

from app.schemas.user_job_search_profile_schema import (
    UserJobSearchProfileResponse,
    UserJobSearchProfileWorkTypeResponse,
)

from app.schemas.user_profile_prompt_schema import (
    UserProfilePromptResponse,
)


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

    # Resolve the user's selected city.
    selected_city_record = None

    if profile.city_id is not None:
        selected_city_record = (
            db.query(City).filter(City.id == profile.city_id).first()
        )

    # Resolve the country through the selected city.
    country = None
    if selected_city_record is not None:
        country = (
            db.query(CountryNew)
            .filter(CountryNew.id == selected_city_record.country_id)
            .first()
        )

    # Resolve the user's selected state.
    selected_state_record = None
    if profile.state_id is not None:
        selected_state_record = (
            db.query(State)
            .filter(State.id == profile.state_id)
            .first()
        )

    # Load active states and cities for the selected country.
    states = []
    cities = []

    if country is not None:
        states = (
            db.query(State.state_name)
            .filter(State.country_id == country.id,
                    State.is_active.is_(True),
            )
            .order_by(State.state_name.asc())
            .all()
        )

        cities = (
            db.query(City.city_name)
            .filter(City.country_id == country.id,
                    City.is_active.is_(True),
            )
            .order_by(City.city_name.asc())
            .all()
        )
    location_details = LocationDetailsResponse(
        country_id=country.id if country else None,
        country_name=country.country_name if country else None,
        selected_state=selected_state_record.state_name if selected_state_record else None,
        selected_city=selected_city_record.city_name if selected_city_record else None,
        states=[state.state_name for state in states],
        cities=[city.city_name for city in cities],
    )
    location_preferences_questions = (
        db.query(LocationPreferenceQuestion).all()
    )
    
    location_preferences_data = []

    for question in location_preferences_questions:
        answers = (
            db.query(LocationPreferenceAnswer)
            .filter(LocationPreferenceAnswer.question_id == question.id)
            .order_by(LocationPreferenceAnswer.id)
            .all()
        )

        location_preferences_data.append(
            LocationPreferenceQuestionResponse(
                question_id=question.id,
                question=question.question,
                answers=[LocationPreferenceAnswerResponse(id=answer.id, answer=answer.answer) for answer in answers]
            )
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

    experiences = (
        db.query(UserProfileExperience)
        .filter(UserProfileExperience.user_profile_id == profile.id)
        .order_by(UserProfileExperience.display_order.asc(),
                  UserProfileExperience.id.asc(),
        )
        .all()
    )

    experience_response = [
        UserProfileExperienceResponse(
            id=experience.id,
            userProfileId=experience.user_profile_id,
            sourceLinkedInExperienceId=(
                experience.linkedin_experience_id
            ),
            title=experience.title,
            company=experience.company_name,
            location=experience.location,
            description=experience.description,
            startDate=experience.start_date,
            endDate=experience.end_date,
            currentlyWorkHere=experience.currently_work_here,
            employmentType=experience.employment_type_id,
            locationType=experience.location_type_id,
            displayOrder=experience.display_order,
            createdAt=experience.created_at,
            updatedAt=experience.updated_at,
        )
        for experience in experiences
    ]

    education = (
        db.query(UserProfileEducation)
        .filter(
            UserProfileEducation.user_profile_id
            == profile.id
        )
        .order_by(
            UserProfileEducation.display_order.asc(),
            UserProfileEducation.id.asc(),
        )
        .all()
    )

    education_response = [
        UserProfileEducationResponse(
            id=education_item.id,
            userProfileId=education_item.user_profile_id,
            sourceLinkedInEducationId=(
                education_item.linkedin_education_id
            ),
            school=education_item.institution_name,
            degree=education_item.degree,
            fieldOfStudy=education_item.field_of_study,
            description=education_item.description,
            startDate=education_item.start_date,
            endDate=education_item.end_date,
            displayOrder=education_item.display_order,
            createdAt=education_item.created_at,
            updatedAt=education_item.updated_at,
        )
        for education_item in education
    ]

    # ---------------------------------------------------------
    # NEW: Company size interests
    # ---------------------------------------------------------

    company_size_interests = (
        db.query(UserCompanySizeInterest)
        .filter(
            UserCompanySizeInterest.user_id
            == user.id
        )
        .order_by(
            UserCompanySizeInterest.company_size_id.asc()
        )
        .all()
    )

    company_size_interest_response = [
        UserCompanySizeInterestResponse(
            id=item.id,
            userId=item.user_id,
            companySizeId=item.company_size_id,
            companyLevelInterestId=(
                item.company_level_interest_id
            ),
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in company_size_interests
    ]

    # ---------------------------------------------------------
    # NEW: Compensation
    # ---------------------------------------------------------

    compensation = (
        db.query(UserProfileCompensation)
        .filter(
            UserProfileCompensation.user_profile_id
            == profile.id
        )
        .first()
    )

    compensation_response = None

    if compensation is not None:
        compensation_response = (
            UserProfileCompensationResponse(
                id=compensation.id,
                userId=user.id,
                cashEquityExpectationId=(
                    compensation.cash_equity_expectation_id
                ),
                expectedMinimumSalaryId=(
                    compensation.expected_minimum_salary_id
                ),
                salaryDurationId=(
                    compensation.salary_duration_id
                ),
                currencyId=compensation.currency_id,
                expectedSalaryAmount=(
                    compensation.expected_salary_amount
                ),
                createdAt=compensation.created_at,
                updatedAt=compensation.updated_at,
            )
        )

    # ---------------------------------------------------------
    # NEW: Job search profile
    # ---------------------------------------------------------

    job_search_profile = (
        db.query(UserJobSearchProfile)
        .filter(
            UserJobSearchProfile.user_id
            == user.id
        )
        .first()
    )

    job_search_profile_response = None
    work_type_response = []

    if job_search_profile is not None:
        job_search_profile_response = (
            UserJobSearchProfileResponse(
                id=job_search_profile.id,
                userId=job_search_profile.user_id,
                jobSearchProfileId=(
                    job_search_profile.job_search_profile_id
                ),
                createdAt=job_search_profile.created_at,
                updatedAt=job_search_profile.updated_at,
            )
        )

        work_types = (
            db.query(UserJobSearchProfileWorkType)
            .filter(
                UserJobSearchProfileWorkType
                .user_job_search_profile_id
                == job_search_profile.id
            )
            .order_by(
                UserJobSearchProfileWorkType.work_type_id.asc()
            )
            .all()
        )

        work_type_response = [
            UserJobSearchProfileWorkTypeResponse(
                userJobSearchProfileId=(
                    item.user_job_search_profile_id
                ),
                workTypeId=item.work_type_id,
                createdAt=item.created_at,
            )
            for item in work_types
        ]

    # ---------------------------------------------------------
    # NEW: Profile prompts
    # ---------------------------------------------------------

    prompts = (
        db.query(UserProfilePrompt)
        .filter(
            UserProfilePrompt.user_profile_id
            == profile.id
        )
        .order_by(
            UserProfilePrompt.display_order.asc()
        )
        .all()
    )

    prompt_response = [
        UserProfilePromptResponse(
            id=item.id,
            userProfileId=item.user_profile_id,
            promptId=item.prompt_id,
            answer=item.answer,
            displayOrder=item.display_order,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in prompts
    ]

    return UserProfileResponse(
        userId=user.id,
        profileId=profile.id,

        firstName=profile.first_name,
        lastName=profile.last_name,
        dateOfBirth=profile.date_of_birth,
        age=profile.age,
        headline=profile.headline,
        founderCount=profile.founder_count,
        priorStartupExperienceId=profile.prior_startup_experience_id,
        workAuthorizationId=profile.work_authorization_id,

        state=profile.state_id,
        city=profile.city_id,

        locationDetails=location_details,

        locationPreferenceQuestions=(
            location_preferences_data
        ),

        locationPreference=[
            {
                "question_id": preference.question_id,
                "selected_answer_id": (
                    preference.selected_answer_id
                ),
            }
            for preference in location_preferences
        ],

        matchingPurpose=profile.matching_purpose_id,
        userRole=profile.user_role_id,
        cofounderRole=profile.cofounder_role_id,

        userSkills=[
            skill.skill_id
            for skill in user_skills
        ],

        cofounderSkills=[
            skill.skill_id
            for skill in cofounder_skills
        ],

        industries=[
            industry.industry_id
            for industry in industries
        ],

        title=profile.title,
        primaryRole=profile.primary_role_id,
        secondaryRole=profile.secondary_role_id,

        bio=profile.bio,
        startupIdea=profile.startup_idea,

        fundingStage=profile.funding_stage_id,
        timeCommitment=profile.time_commitment_id,
        riskAppetite=profile.risk_appetite_id,

        employmentType=profile.employment_type_id,
        
        # NEW
        experiences=experience_response,
        education=education_response,
        companySizeInterests=(
            company_size_interest_response
        ),
        compensation=compensation_response,
        jobSearchProfile=(
            job_search_profile_response
        ),
        jobSearchProfileWorkTypes=(
            work_type_response
        ),
        prompts=prompt_response,

        linkedinUrl=profile.linkedin_url,
        linkedinUsername=profile.linkedin_username,

        linkedinProfilePreview=(
            LinkedInProfilePreview(
                headline=(
                    profile.linkedin_profile_preview_headline
                ),
                firstOrganization=(
                    profile.linkedin_profile_preview_first_organization
                ),
                firstEducationInstitution=(
                    profile.linkedin_profile_preview_first_education_institution
                ),
                firstLocation=(
                    profile.linkedin_profile_preview_first_location
                ),
                connections=(
                    profile.linkedin_profile_preview_connections
                ),
            )
            if any(value is not None for value in preview_fields)
            else None
        ),

        linkedinProfilePictureUrl=(
            profile.linkedin_profile_picture_url
        ),

        pendingProfileImageUri=(
            profile.pending_profile_image_uri
        ),

        pendingProfileImageSource=(
            profile.pending_profile_image_source
        ),

        profileImageRotation=(
            profile.profile_image_rotation
        ),

        profileImageScale=(
            profile.profile_image_scale
        ),

        profileImageTranslateX=(
            profile.profile_image_translate_x
        ),

        profileImageTranslateY=(
            profile.profile_image_translate_y
        ),

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


def _sync_profile_experiences(
    db: Session,
    profile: UserProfile,
    experiences,
):
    existing = (
        db.query(UserProfileExperience)
        .filter(
            UserProfileExperience.user_profile_id
            == profile.id
        )
        .all()
    )

    existing_by_id = {
        item.id: item
        for item in existing
    }

    incoming_ids = {
        item.id
        for item in experiences
        if item.id is not None
    }

    for item in experiences:

        if item.id is not None:

            existing_item = existing_by_id.get(item.id)

            if existing_item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Experience id {item.id} "
                        "does not belong to this profile."
                    ),
                )

            existing_item.linkedin_experience_id = (
                item.sourceLinkedInExperienceId
            )
            existing_item.title = item.title
            existing_item.company_name = item.company
            existing_item.location = item.location
            existing_item.description = item.description
            existing_item.start_date = item.startDate
            existing_item.end_date = item.endDate
            existing_item.currently_work_here = (
                item.currentlyWorkHere
            )
            existing_item.employment_type_id = (
                item.employmentType
            )
            existing_item.location_type_id = (
                item.locationType
            )
            existing_item.display_order = (
                item.displayOrder
            )

        else:

            db.add(
                UserProfileExperience(
                    user_profile_id=profile.id,
                    linkedin_experience_id=(
                        item.sourceLinkedInExperienceId
                    ),
                    title=item.title,
                    company_name=item.company,
                    location=item.location,
                    description=item.description,
                    start_date=item.startDate,
                    end_date=item.endDate,
                    currently_work_here=(
                        item.currentlyWorkHere
                    ),
                    employment_type_id=item.employmentType,
                    location_type_id=item.locationType,
                    display_order=item.displayOrder,
                )
            )

    # Anything previously stored but no longer sent
    # by ProfileEditScreen is removed.
    for existing_item in existing:
        if existing_item.id not in incoming_ids:
            db.delete(existing_item)


def _sync_profile_education(
    db: Session,
    profile: UserProfile,
    education,
):
    existing = (
        db.query(UserProfileEducation)
        .filter(
            UserProfileEducation.user_profile_id
            == profile.id
        )
        .all()
    )

    existing_by_id = {
        item.id: item
        for item in existing
    }

    incoming_ids = {
        item.id
        for item in education
        if item.id is not None
    }

    for item in education:

        if item.id is not None:

            existing_item = existing_by_id.get(item.id)

            if existing_item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Education id {item.id} "
                        "does not belong to this profile."
                    ),
                )

            existing_item.linkedin_education_id = (
                item.sourceLinkedInEducationId
            )
            existing_item.institution_name = item.school
            existing_item.degree = item.degree
            existing_item.field_of_study = (
                item.fieldOfStudy
            )
            existing_item.description = item.description
            existing_item.start_date = item.startDate
            existing_item.end_date = item.endDate
            existing_item.display_order = (
                item.displayOrder
            )

        else:

            db.add(
                UserProfileEducation(
                    user_profile_id=profile.id,
                    linkedin_education_id=(
                        item.sourceLinkedInEducationId
                    ),
                    institution_name=item.school,
                    degree=item.degree,
                    field_of_study=item.fieldOfStudy,
                    description=item.description,
                    start_date=item.startDate,
                    end_date=item.endDate,
                    display_order=item.displayOrder,
                )
            )

    for existing_item in existing:
        if existing_item.id not in incoming_ids:
            db.delete(existing_item)

def _sync_company_size_interests(
    db: Session,
    user: User,
    interests,
):
    db.query(UserCompanySizeInterest).filter(
        UserCompanySizeInterest.user_id == user.id
    ).delete(
        synchronize_session=False
    )

    for item in interests:
        db.add(
            UserCompanySizeInterest(
                user_id=user.id,
                company_size_id=item.companySizeId,
                company_level_interest_id=(
                    item.companyLevelInterestId
                ),
            )
        )

def _sync_profile_compensation(
    db: Session,
    profile: UserProfile,
    compensation,
):
    existing = (
        db.query(UserProfileCompensation)
        .filter(
            UserProfileCompensation.user_profile_id
            == profile.id
        )
        .first()
    )

    if compensation is None:

        if existing is not None:
            db.delete(existing)

        return

    if existing is None:

        db.add(
            UserProfileCompensation(
                user_profile_id=profile.id,
                cash_equity_expectation_id=(
                    compensation.cashEquityExpectationId
                ),
                expected_minimum_salary_id=(
                    compensation.expectedMinimumSalaryId
                ),
                salary_duration_id=(
                    compensation.salaryDurationId
                ),
                currency_id=(
                    compensation.currencyId
                ),
                expected_salary_amount=(
                    compensation.expectedSalaryAmount
                ),
            )
        )

    else:

        existing.cash_equity_expectation_id = (
            compensation.cashEquityExpectationId
        )

        existing.expected_minimum_salary_id = (
            compensation.expectedMinimumSalaryId
        )

        existing.salary_duration_id = (
            compensation.salaryDurationId
        )

        existing.currency_id = (
            compensation.currencyId
        )

        existing.expected_salary_amount = (
            compensation.expectedSalaryAmount
        )
def _sync_job_search_profile(
    db: Session,
    user: User,
    job_search_profile,
):
    existing = (
        db.query(UserJobSearchProfile)
        .filter(
            UserJobSearchProfile.user_id == user.id
        )
        .first()
    )

    if job_search_profile is None:

        if existing is not None:
            db.delete(existing)

        return None

    if existing is None:

        existing = UserJobSearchProfile(
            user_id=user.id,
            job_search_profile_id=(
                job_search_profile.jobSearchProfileId
            ),
        )

        db.add(existing)
        db.flush()

    else:

        existing.job_search_profile_id = (
            job_search_profile.jobSearchProfileId
        )

    return existing

def _sync_job_search_work_types(
    db: Session,
    job_search_profile,
    work_types,
):
    if job_search_profile is None:
        return

    db.query(
        UserJobSearchProfileWorkType
    ).filter(
        UserJobSearchProfileWorkType
        .user_job_search_profile_id
        == job_search_profile.id
    ).delete(
        synchronize_session=False
    )

    for item in work_types:
        db.add(
            UserJobSearchProfileWorkType(
                user_job_search_profile_id=(
                    job_search_profile.id
                ),
                work_type_id=item.workTypeId,
            )
        )

def _sync_profile_prompts(
    db: Session,
    profile: UserProfile,
    prompts,
):
    existing = (
        db.query(UserProfilePrompt)
        .filter(
            UserProfilePrompt.user_profile_id
            == profile.id
        )
        .all()
    )

    existing_by_id = {
        item.id: item
        for item in existing
    }

    incoming_ids = {
        item.id
        for item in prompts
        if item.id is not None
    }

    for item in prompts:

        if item.id is not None:

            existing_item = existing_by_id.get(item.id)

            if existing_item is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Prompt id {item.id} "
                        "does not belong to this profile."
                    ),
                )

            existing_item.prompt_id = item.promptId
            existing_item.answer = item.answer
            existing_item.display_order = (
                item.displayOrder
            )

        else:

            db.add(
                UserProfilePrompt(
                    user_profile_id=profile.id,
                    prompt_id=item.promptId,
                    answer=item.answer,
                    display_order=item.displayOrder,
                )
            )

    for existing_item in existing:
        if existing_item.id not in incoming_ids:
            db.delete(existing_item)

@router.patch(
    "/users/me/profile",
    response_model=UserProfileUpsertResponse,
)
def upsert_my_profile(
    payload: UserProfileUpsertRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(
        authorization=authorization,
        db=db,
    )

    try:

        # -----------------------------------------------------
        # LinkedIn profile
        # -----------------------------------------------------

        linkedin_profile = (
            db.query(LinkedInProfile)
            .filter(
                LinkedInProfile.user_id == user.id
            )
            .first()
        )

        # -----------------------------------------------------
        # Main user profile
        # -----------------------------------------------------

        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.user_id == user.id
            )
            .first()
        )

        if profile is None:
            profile = UserProfile(
                user_id=user.id
            )

            db.add(profile)

        # -----------------------------------------------------
        # Basic profile
        # -----------------------------------------------------

        profile.first_name = payload.firstName
        profile.last_name = payload.lastName
        profile.date_of_birth = payload.dateOfBirth
        profile.age = payload.age
        profile.headline = payload.headline
        profile.founder_count = payload.founderCount
        profile.prior_startup_experience_id = payload.priorStartupExperienceId
        profile.work_authorization_id = payload.workAuthorizationId

        profile.state_id = payload.state
        profile.city_id = payload.city

        profile.matching_purpose_id = (
            payload.matchingPurpose
        )

        profile.user_role_id = payload.userRole

        profile.cofounder_role_id = (
            payload.cofounderRole
        )

        profile.title = payload.title

        profile.primary_role_id = (
            payload.primaryRole
        )

        profile.secondary_role_id = (
            payload.secondaryRole
        )

        profile.bio = payload.bio

        profile.startup_idea = (
            payload.startupIdea
        )

        profile.funding_stage_id = (
            payload.fundingStage
        )

        profile.time_commitment_id = (
            payload.timeCommitment
        )

        profile.risk_appetite_id = (
            payload.riskAppetite
        )

        profile.employment_type_id = (
            payload.employmentType
        )

        profile.company_name = (
            payload.companyName
        )

        profile.experience_location = (
            payload.experienceLocation
        )

        profile.location_type_id = (
            payload.locationType
        )

        profile.start_date = payload.startDate

        profile.currently_work_here = (
            payload.currentlyWorkHere
        )

        profile.end_date = payload.endDate

        profile.linkedin_url = (
            payload.linkedinUrl
        )

        profile.linkedin_username = (
            payload.linkedinUsername
        )

        profile.linkedin_profile_picture_url = (
            payload.linkedinProfilePictureUrl
        )

        profile.pending_profile_image_uri = (
            payload.pendingProfileImageUri
        )

        profile.pending_profile_image_source = (
            payload.pendingProfileImageSource
        )

        profile.profile_image_rotation = (
            payload.profileImageRotation
        )

        profile.profile_image_scale = (
            payload.profileImageScale
        )

        profile.profile_image_translate_x = (
            payload.profileImageTranslateX
        )

        profile.profile_image_translate_y = (
            payload.profileImageTranslateY
        )

        profile.profile_image_uri = (
            payload.profileImageUri
        )

        profile.profile_image_source = (
            payload.profileImageSource
        )

        profile.linkedin_profile_id = (
            linkedin_profile.id
            if linkedin_profile
            else None
        )

        # -----------------------------------------------------
        # LinkedIn preview
        # -----------------------------------------------------

        if payload.linkedinProfilePreview is not None:

            profile.linkedin_profile_preview_headline = (
                payload.linkedinProfilePreview.headline
            )

            profile.linkedin_profile_preview_first_organization = (
                payload.linkedinProfilePreview.firstOrganization
            )

            profile.linkedin_profile_preview_first_education_institution = (
                payload.linkedinProfilePreview.firstEducationInstitution
            )

            profile.linkedin_profile_preview_first_location = (
                payload.linkedinProfilePreview.firstLocation
            )

            profile.linkedin_profile_preview_connections = (
                payload.linkedinProfilePreview.connections
            )

        else:

            profile.linkedin_profile_preview_headline = None
            profile.linkedin_profile_preview_first_organization = None
            profile.linkedin_profile_preview_first_education_institution = None
            profile.linkedin_profile_preview_first_location = None
            profile.linkedin_profile_preview_connections = None

        # -----------------------------------------------------
        # Profile image crop
        # -----------------------------------------------------

        if payload.profileImageCropRect is not None:

            profile.profile_image_crop_x = (
                payload.profileImageCropRect.x
            )

            profile.profile_image_crop_y = (
                payload.profileImageCropRect.y
            )

            profile.profile_image_crop_width = (
                payload.profileImageCropRect.width
            )

            profile.profile_image_crop_height = (
                payload.profileImageCropRect.height
            )

        else:

            profile.profile_image_crop_x = None
            profile.profile_image_crop_y = None
            profile.profile_image_crop_width = None
            profile.profile_image_crop_height = None

        # -----------------------------------------------------
        # Flush first so a newly-created profile gets its ID.
        # -----------------------------------------------------

        db.flush()

        # =====================================================
        # Existing profile collections
        # =====================================================

        # -----------------------------------------------------
        # Location preferences
        # -----------------------------------------------------

        db.query(
            UserProfileLocationPreference
        ).filter(
            UserProfileLocationPreference
            .user_profile_id
            == profile.id
        ).delete(
            synchronize_session=False
        )

        for location_preference in (
            payload.locationPreference
        ):

            db.add(
                UserProfileLocationPreference(
                    user_profile_id=profile.id,
                    question_id=(
                        location_preference.question_id
                    ),
                    selected_answer_id=(
                        location_preference
                        .selected_answer_id
                    ),
                )
            )

        # -----------------------------------------------------
        # User skills
        # -----------------------------------------------------

        db.query(
            UserProfileUserSkill
        ).filter(
            UserProfileUserSkill
            .user_profile_id
            == profile.id
        ).delete(
            synchronize_session=False
        )

        for skill_id in payload.userSkills:

            db.add(
                UserProfileUserSkill(
                    user_profile_id=profile.id,
                    skill_id=skill_id,
                )
            )

        # -----------------------------------------------------
        # Cofounder skills
        # -----------------------------------------------------

        db.query(
            UserProfileCofounderSkill
        ).filter(
            UserProfileCofounderSkill
            .user_profile_id
            == profile.id
        ).delete(
            synchronize_session=False
        )

        for skill_id in payload.cofounderSkills:

            db.add(
                UserProfileCofounderSkill(
                    user_profile_id=profile.id,
                    skill_id=skill_id,
                )
            )

        # -----------------------------------------------------
        # Industries
        # -----------------------------------------------------

        db.query(
            UserProfileIndustry
        ).filter(
            UserProfileIndustry
            .user_profile_id
            == profile.id
        ).delete(
            synchronize_session=False
        )

        for industry_id in payload.industries:

            db.add(
                UserProfileIndustry(
                    user_profile_id=profile.id,
                    industry_id=industry_id,
                )
            )

        # =====================================================
        # NEW SEVEN TABLES
        # =====================================================

        # -----------------------------------------------------
        # 1. Experiences
        # -----------------------------------------------------

        _sync_profile_experiences(
            db=db,
            profile=profile,
            experiences=payload.experiences,
        )

        # -----------------------------------------------------
        # 2. Education
        # -----------------------------------------------------

        _sync_profile_education(
            db=db,
            profile=profile,
            education=payload.education,
        )

        # -----------------------------------------------------
        # 3. Company size interests
        # -----------------------------------------------------

        _sync_company_size_interests(
            db=db,
            user=user,
            interests=payload.companySizeInterests,
        )

        # -----------------------------------------------------
        # 4. Compensation
        # -----------------------------------------------------

        _sync_profile_compensation(
            db=db,
            profile=profile,
            compensation=payload.compensation,
        )

        # -----------------------------------------------------
        # 5. Job search profile
        # -----------------------------------------------------

        job_search_profile = (
            _sync_job_search_profile(
                db=db,
                user=user,
                job_search_profile=(
                    payload.jobSearchProfile
                ),
            )
        )

        # -----------------------------------------------------
        # 6. Job search work types
        # -----------------------------------------------------

        _sync_job_search_work_types(
            db=db,
            job_search_profile=job_search_profile,
            work_types=(
                payload.jobSearchProfileWorkTypes
            ),
        )

        # -----------------------------------------------------
        # 7. Prompts
        # -----------------------------------------------------

        _sync_profile_prompts(
            db=db,
            profile=profile,
            prompts=payload.prompts,
        )

        # -----------------------------------------------------
        # Commit everything atomically
        # -----------------------------------------------------

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
            detail=(
                "Invalid foreign key reference or "
                "duplicate profile data in request payload."
            ),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to upsert user profile: {str(exc)}"
            ),
        ) from exc


@router.get("/users/me/profile/industries", response_model=list[IndustryResponse])
def get_my_industries(
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

    user_industries = (
        db.query(Industry)
        .join(UserProfileIndustry, Industry.id == UserProfileIndustry.industry_id)
        .filter(UserProfileIndustry.user_profile_id == profile.id)
        .order_by(Industry.id.asc())
        .all()
    )
    return user_industries

@router.get("/users/me/profile/skills", response_model=list[UserSkillResponse])
def get_user_skills(
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

    user_skills = (
        db.query(UserSkill)
        .join(UserProfileUserSkill, UserSkill.id == UserProfileUserSkill.skill_id)
        .filter(UserProfileUserSkill.user_profile_id == profile.id)
        .order_by(UserSkill.id.asc())
        .all()
    )
    return user_skills


@router.get("/users/me/profile/linkedin-details", response_model=LinkedInProfileDetailsResponse)
def get_my_linkedin_details(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    linkedin_profile = db.query(LinkedInProfile).filter(LinkedInProfile.user_id == user.id).first()
    if linkedin_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LinkedIn profile not found.",
        )

    experiences = (
        db.query(LinkedInProfileExperience)
        .filter(LinkedInProfileExperience.profile_id == linkedin_profile.id)
        .order_by(LinkedInProfileExperience.start_year.desc(), LinkedInProfileExperience.start_month.desc())
        .all()
    )
    educations = (
        db.query(LinkedInProfileEducation)
        .filter(LinkedInProfileEducation.profile_id == linkedin_profile.id)
        .order_by(LinkedInProfileEducation.start_year.desc(), LinkedInProfileEducation.start_month.desc())
        .all()
    )

    return LinkedInProfileDetailsResponse(experience=experiences, education=educations)


