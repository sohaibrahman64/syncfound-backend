from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.linkedin_profile_model import (
    LinkedInProfile,
    LinkedInProfileEducation,
    LinkedInProfileExperience,
)
from app.models.location_preference_model import LocationPreferenceAnswer
from app.models.profile_edit_model import (
    UserJobSearchProfile,
    UserProfileCompanySizeInterest,
    UserProfileCompensation,
    UserProfileCommitmentLevel,
    UserProfileEdit,
    UserProfileEditEducation,
    UserProfileEditExperience,
    UserProfileEquitySplit,
    UserProfileMatchingGoal,
    UserProfilePriorStartupExperience,
    UserProfilePrompt,
    UserProfileWorkAuthorization,
)
from app.models.user_profile_model import (
    UserProfile,
    UserProfileIndustry,
    UserProfileLocationPreference,
    UserProfileUserSkill,
)
from app.models.city_model import City
from app.routes.user_profile_route import _get_authenticated_user
from app.schemas.profile_edit_schema import (
    EducationEdit,
    ExperienceEdit,
    FounderProfileEdit,
    TalentProfileEdit,
    UserProfileEditRequest,
    UserProfileEditResponse,
)


router = APIRouter(prefix="/api/v1", tags=["User Profile"])


def _present_values(payload: Any, field_mapping: dict[str, str]) -> dict[str, Any]:
    return {
        model_field: getattr(payload, request_field)
        for request_field, model_field in field_mapping.items()
        if request_field in payload.model_fields_set
    }


def _upsert_profile_row(
    db: Session,
    model: Any,
    profile_id: int,
    row_id: int | None,
    values: dict[str, Any],
):
    row = db.get(model, row_id) if row_id is not None else None
    if row is not None and row.user_profile_id != profile_id:
        row = None
    if row is None:
        row = (
            db.query(model)
            .filter(model.user_profile_id == profile_id)
            .order_by(model.id.asc())
            .first()
        )
    if row is None:
        row = model(user_profile_id=profile_id)
        db.add(row)
    for field, value in values.items():
        setattr(row, field, value)
    db.flush()
    return row


def _sync_ordered_rows(
    db: Session,
    model: Any,
    profile_id: int,
    values: list[Any],
    apply_value,
    *,
    order_field: str = "id",
    profile_field: str = "user_profile_id",
):
    rows = (
        db.query(model)
        .filter(getattr(model, profile_field) == profile_id)
        .order_by(getattr(model, order_field).asc(), model.id.asc())
        .all()
    )
    result = []
    for index, value in enumerate(values):
        row = rows[index] if index < len(rows) else model(**{profile_field: profile_id})
        if index >= len(rows):
            db.add(row)
        apply_value(row, value)
        result.append(row)
    for row in rows[len(values):]:
        db.delete(row)
    db.flush()
    return result


def _as_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_month(value: str | int | None) -> str | None:
    if value is None or str(value).strip().lower() in {"", "mm", "month"}:
        return None
    return str(value).strip()


def _as_date(year: str | int | None, month: str | int | None) -> date | None:
    year_value = _as_int(year)
    month_value = _as_int(month)
    if year_value is None or month_value is None or not 1 <= month_value <= 12:
        return None
    try:
        return date(year_value, month_value, 1)
    except ValueError:
        return None


def _updated_date(
    current: date | None,
    year: str | int | None,
    month: str | int | None,
    *,
    year_was_sent: bool,
    month_was_sent: bool,
) -> date | None:
    if not year_was_sent and not month_was_sent:
        return current
    year_value = _as_int(year) if year_was_sent else (current.year if current else None)
    month_value = _as_int(month) if month_was_sent else (current.month if current else None)
    return _as_date(year_value, month_value)


def _apply_linkedin_experience(row: LinkedInProfileExperience, item: ExperienceEdit) -> None:
    mapping = {
        "title": "title",
        "company": "company",
        "description": "description",
        "currentlyWorkHere": "is_current",
    }
    for request_field, model_field in mapping.items():
        if request_field in item.model_fields_set:
            setattr(row, model_field, getattr(item, request_field))
    for request_field, model_field in (
        ("startYear", "start_year"),
        ("endYear", "end_year"),
    ):
        if request_field in item.model_fields_set:
            setattr(row, model_field, _as_int(getattr(item, request_field)))
    for request_field, model_field in (
        ("startMonth", "start_month"),
        ("endMonth", "end_month"),
    ):
        if request_field in item.model_fields_set:
            setattr(row, model_field, _as_month(getattr(item, request_field)))


def _apply_linkedin_education(row: LinkedInProfileEducation, item: EducationEdit) -> None:
    mapping = {
        "school": "school",
        "degree": "degree",
        "fieldOfStudy": "field_of_study",
        "description": "description",
    }
    for request_field, model_field in mapping.items():
        if request_field in item.model_fields_set:
            setattr(row, model_field, getattr(item, request_field))
    for request_field, model_field in (
        ("startYear", "start_year"),
        ("endYear", "end_year"),
    ):
        if request_field in item.model_fields_set:
            setattr(row, model_field, _as_int(getattr(item, request_field)))
    for request_field, model_field in (
        ("startMonth", "start_month"),
        ("endMonth", "end_month"),
    ):
        if request_field in item.model_fields_set:
            setattr(row, model_field, _as_month(getattr(item, request_field)))


def _apply_edit_experience(row: UserProfileEditExperience, item: ExperienceEdit) -> None:
    mapping = {
        "title": "title",
        "company": "company",
        "description": "description",
        "currentlyWorkHere": "is_currently_working",
    }
    for request_field, model_field in mapping.items():
        if request_field in item.model_fields_set:
            setattr(row, model_field, getattr(item, request_field))
    if "startYear" in item.model_fields_set or "startMonth" in item.model_fields_set:
        row.start_date = _updated_date(
            row.start_date,
            item.startYear,
            item.startMonth,
            year_was_sent="startYear" in item.model_fields_set,
            month_was_sent="startMonth" in item.model_fields_set,
        )
    if item.currentlyWorkHere is True:
        row.end_date = None
    elif "endYear" in item.model_fields_set or "endMonth" in item.model_fields_set:
        row.end_date = _updated_date(
            row.end_date,
            item.endYear,
            item.endMonth,
            year_was_sent="endYear" in item.model_fields_set,
            month_was_sent="endMonth" in item.model_fields_set,
        )


def _apply_edit_education(row: UserProfileEditEducation, item: EducationEdit) -> None:
    mapping = {
        "school": "school",
        "degree": "degree",
        "fieldOfStudy": "field_of_study",
        "description": "description",
    }
    for request_field, model_field in mapping.items():
        if request_field in item.model_fields_set:
            setattr(row, model_field, getattr(item, request_field))
    if "startYear" in item.model_fields_set or "startMonth" in item.model_fields_set:
        row.start_date = _updated_date(
            row.start_date,
            item.startYear,
            item.startMonth,
            year_was_sent="startYear" in item.model_fields_set,
            month_was_sent="startMonth" in item.model_fields_set,
        )
    if "endYear" in item.model_fields_set or "endMonth" in item.model_fields_set:
        row.end_date = _updated_date(
            row.end_date,
            item.endYear,
            item.endMonth,
            year_was_sent="endYear" in item.model_fields_set,
            month_was_sent="endMonth" in item.model_fields_set,
        )


def _to_boolean(value: bool | str | None) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"yes", "y", "true", "1"}:
        return True
    if normalized in {"no", "n", "false", "0"}:
        return False
    raise HTTPException(status_code=422, detail="isHiring must be a boolean or Yes/No value.")


def _equity_range(value: int | str | None) -> int | None:
    if value is None or (isinstance(value, str) and value.strip().upper() in {"", "NA", "N/A"}):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Equity ranges must be integers or NA.") from exc


def _resolve_profile_pointer(
    db: Session,
    current_edit: UserProfileEdit | None,
    pointer_field: str,
    model: Any,
    profile_id: int,
) -> int | None:
    existing_id = getattr(current_edit, pointer_field, None) if current_edit else None
    if existing_id is not None:
        existing_row = db.get(model, existing_id)
        if existing_row is not None and existing_row.user_profile_id == profile_id:
            return existing_id
    row = (
        db.query(model)
        .filter(model.user_profile_id == profile_id)
        .order_by(model.id.asc())
        .first()
    )
    return row.id if row is not None else None


def _validate_active_branch(raw_value: Any, schema: Any, branch_name: str) -> Any:
    if raw_value is None:
        return None
    try:
        return TypeAdapter(schema).validate_python(raw_value)
    except ValidationError as exc:
        errors = [
            {
                "loc": (branch_name, *error["loc"]),
                "msg": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors(include_context=False)
        ]
        raise HTTPException(status_code=422, detail=errors) from exc


@router.patch("/users/me/profile/edit", response_model=UserProfileEditResponse)
def edit_my_profile(
    payload: UserProfileEditRequest,
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user = _get_authenticated_user(authorization=authorization, db=db)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")

    edit_rows = (
        db.query(UserProfileEdit)
        .filter(UserProfileEdit.user_profile_id == profile.id)
        .order_by(UserProfileEdit.id.asc())
        .all()
    )
    current_edit = edit_rows[0] if edit_rows else None
    current_edit_values = {
        column.name: getattr(current_edit, column.name)
        for column in UserProfileEdit.__table__.columns
    } if current_edit else {}

    supplied_selectors = [
        value
        for value in (payload.userDescribedAs, payload.userSelectedAs)
        if value is not None
    ]
    if len(set(supplied_selectors)) > 1:
        raise HTTPException(
            status_code=422,
            detail="userDescribedAs and userSelectedAs must have the same value when both are provided.",
        )
    requested_selector = supplied_selectors[0] if supplied_selectors else None
    if requested_selector is not None and requested_selector not in {1, 2, 3}:
        raise HTTPException(status_code=422, detail="The profile selector must be 1 (Founder), 2 (Talent), or 3 (Both).")

    effective_selector = (
        requested_selector
        if requested_selector is not None
        else current_edit_values.get("user_described_as_id")
    )
    if effective_selector in {1, 2, 3}:
        founder_active = effective_selector in {1, 3}
        talent_active = effective_selector in {2, 3}
    else:
        # Preserve PATCH behavior for legacy records that have no selector yet:
        # validate any supplied branch, and require the selector to initialize
        # the edit row below.
        founder_active = payload.userBackgroundAsAFounder is not None
        talent_active = payload.userBackgroundAsATalent is not None

    payload.userBackgroundAsAFounder = (
        _validate_active_branch(payload.userBackgroundAsAFounder, FounderProfileEdit, "userBackgroundAsAFounder")
        if founder_active
        else None
    )
    payload.userBackgroundAsATalent = (
        _validate_active_branch(payload.userBackgroundAsATalent, TalentProfileEdit, "userBackgroundAsATalent")
        if talent_active
        else None
    )

    linked_in_profile = None
    if payload.userProfile and payload.userProfile.experiences and (
        payload.userProfile.experiences.linkedinJobExperiences is not None
    ):
        linked_in_profile = (
            db.query(LinkedInProfile)
            .filter(LinkedInProfile.user_id == user.id)
            .first()
        )
        if linked_in_profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A LinkedIn profile must exist before its experiences can be edited.",
            )
    if payload.userProfile and payload.userProfile.education and payload.userProfile.education.linkedInEducation is not None:
        if linked_in_profile is None:
            linked_in_profile = (
                db.query(LinkedInProfile)
                .filter(LinkedInProfile.user_id == user.id)
                .first()
            )
        if linked_in_profile is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A LinkedIn profile must exist before its education can be edited.",
            )

    try:
        # The edit row points at child rows with ON DELETE CASCADE constraints in the
        # supplied schema. Remove it first, then recreate it after child updates.
        for edit_row in edit_rows:
            db.delete(edit_row)
        db.flush()

        if "profileImageUri" in payload.model_fields_set:
            profile.profile_image_uri = payload.profileImageUri

        if payload.userBackgroundAsATalent and payload.userBackgroundAsATalent.bioExperience:
            bio = payload.userBackgroundAsATalent.bioExperience
            values = _present_values(
                bio,
                {
                    "title": "title",
                    "primaryRole": "primary_role_id",
                    "secondaryRole": "secondary_role_id",
                    "yearsOfExperience": "years_of_experience",
                    "bio": "bio",
                    "startupIdea": "startup_idea",
                    "fundingStage": "funding_stage_id",
                    "riskAppetite": "risk_appetite_id",
                    "employmentType": "employment_type_id",
                    "companyName": "company_name",
                    "location": "experience_location",
                    "locationType": "location_type_id",
                },
            )
            for field, value in values.items():
                setattr(profile, field, value)

        if payload.userProfile:
            details = payload.userProfile
            if "name" in details.model_fields_set and details.name is not None:
                name = details.name.strip()
                if not name:
                    raise HTTPException(status_code=422, detail="name cannot be empty.")
                first_name, _, last_name = name.partition(" ")
                profile.first_name = first_name
                profile.last_name = last_name.strip()
            if "age" in details.model_fields_set:
                profile.age = details.age
            if "linkedInUrl" in details.model_fields_set:
                profile.linkedin_url = details.linkedInUrl
            if details.location:
                location = details.location
                city_was_sent = "city" in location.model_fields_set and location.city is not None
                country_was_sent = "country" in location.model_fields_set and location.country is not None
                if city_was_sent or country_was_sent:
                    city_id = location.city if city_was_sent else profile.city_id
                    if city_id is not None:
                        city = db.query(City).filter(City.id == city_id).first()
                        if city is None:
                            raise HTTPException(status_code=400, detail="The requested city was not found.")
                        if country_was_sent and city.country_id != location.country:
                            raise HTTPException(
                                status_code=400,
                                detail="The requested city does not belong to the requested country.",
                            )
                        if city_was_sent:
                            profile.city_id = city.id
                if location.preference is not None:
                    db.query(UserProfileLocationPreference).filter(
                        UserProfileLocationPreference.user_profile_id == profile.id
                    ).delete(synchronize_session=False)
                    for preference in location.preference:
                        answer = (
                            db.query(LocationPreferenceAnswer)
                            .filter(
                                LocationPreferenceAnswer.id == preference.selected_answer_id,
                                LocationPreferenceAnswer.question_id == preference.question_id,
                            )
                            .first()
                        )
                        if answer is None:
                            raise HTTPException(
                                status_code=400,
                                detail="A selected location preference answer does not belong to its question.",
                            )
                        db.add(
                            UserProfileLocationPreference(
                                user_profile_id=profile.id,
                                question_id=preference.question_id,
                                selected_answer_id=preference.selected_answer_id,
                            )
                        )

            if details.experiences:
                experiences = details.experiences
                if experiences.linkedinJobExperiences is not None:
                    def apply_linkedin_experience(row, item):
                        row.profile_id = linked_in_profile.id
                        _apply_linkedin_experience(row, item)

                    _sync_ordered_rows(
                        db,
                        LinkedInProfileExperience,
                        linked_in_profile.id,
                        experiences.linkedinJobExperiences,
                        apply_linkedin_experience,
                        profile_field="profile_id",
                    )
                if experiences.additionalJobExperiences is not None:
                    _sync_ordered_rows(
                        db,
                        UserProfileEditExperience,
                        profile.id,
                        experiences.additionalJobExperiences,
                        _apply_edit_experience,
                    )

            if details.education:
                education = details.education
                if education.linkedInEducation is not None:
                    def apply_linkedin_education(row, item):
                        row.profile_id = linked_in_profile.id
                        _apply_linkedin_education(row, item)

                    _sync_ordered_rows(
                        db,
                        LinkedInProfileEducation,
                        linked_in_profile.id,
                        education.linkedInEducation,
                        apply_linkedin_education,
                        profile_field="profile_id",
                    )
                if education.additionalEducation is not None:
                    _sync_ordered_rows(
                        db,
                        UserProfileEditEducation,
                        profile.id,
                        education.additionalEducation,
                        _apply_edit_education,
                    )

        prompt_rows = None
        if payload.userPrompts is not None:
            if not payload.userPrompts:
                raise HTTPException(
                    status_code=400,
                    detail="At least one user prompt is required by the profile edit schema.",
                )

            prompt_order = 0

            def apply_prompt(row, item):
                nonlocal prompt_order
                try:
                    row.prompt_id = int(item.prompt)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=422, detail="Prompt IDs must be integers.") from exc
                row.answer = item.answer
                prompt_order += 1
                row.display_order = prompt_order

            prompt_rows = _sync_ordered_rows(
                db,
                UserProfilePrompt,
                profile.id,
                payload.userPrompts,
                apply_prompt,
                order_field="display_order",
            )

        founder_rows: dict[str, Any] = {}
        founder = payload.userBackgroundAsAFounder
        if founder:
            if founder.matchingGoal:
                matching_values = _present_values(
                    founder.matchingGoal,
                    {"answer": "matching_goal_id", "isHiring": "is_hiring"},
                )
                if "is_hiring" in matching_values:
                    matching_values["is_hiring"] = _to_boolean(matching_values["is_hiring"])
                if matching_values:
                    founder_rows["matching_goal"] = _upsert_profile_row(
                        db,
                        UserProfileMatchingGoal,
                        profile.id,
                        current_edit_values.get("user_profile_matching_goal_id"),
                        matching_values,
                    )

            if founder.commitmentLevel is not None:
                founder_rows["commitment"] = _upsert_profile_row(
                    db,
                    UserProfileCommitmentLevel,
                    profile.id,
                    current_edit_values.get("user_profile_commitment_level_id"),
                    {"commitment_level_id": founder.commitmentLevel},
                )

            if founder.equitySplit:
                equity_values = _present_values(
                    founder.equitySplit,
                    {
                        "answer": "equity_split_id",
                        "minEquityRange": "min_equity_range",
                        "maxEquityRange": "max_equity_range",
                    },
                )
                for field in ("min_equity_range", "max_equity_range"):
                    if field in equity_values:
                        equity_values[field] = _equity_range(equity_values[field])
                if equity_values:
                    founder_rows["equity_split"] = _upsert_profile_row(
                        db,
                        UserProfileEquitySplit,
                        profile.id,
                        current_edit_values.get("user_profile_equity_split_id"),
                        equity_values,
                    )

            if founder.userSkills is not None:
                db.query(UserProfileUserSkill).filter(
                    UserProfileUserSkill.user_profile_id == profile.id
                ).delete(synchronize_session=False)
                for skill_id in dict.fromkeys(founder.userSkills):
                    db.add(UserProfileUserSkill(user_profile_id=profile.id, skill_id=skill_id))

        talent_rows: dict[str, Any] = {}
        talent = payload.userBackgroundAsATalent
        import pdb; pdb.set_trace();
        if talent:
            if talent.jobSearchProfile:
                search = talent.jobSearchProfile
                current_search_id = current_edit_values.get("user_job_search_profile_id")
                current_search_row = db.get(UserJobSearchProfile, current_search_id) if current_search_id else None
                if current_search_row is not None:
                    # Older rows may predate the profile ownership column added by
                    # this endpoint's migration. The edit row identifies its owner.
                    current_search_row.user_profile_id = profile.id
                    db.flush()
                existing_search_rows = (
                    db.query(UserJobSearchProfile)
                    .filter(UserJobSearchProfile.user_profile_id == profile.id)
                    .order_by(UserJobSearchProfile.id.asc())
                    .all()
                )
                if search.jobSearchWorkType is not None:
                    if not search.jobSearchWorkType:
                        raise HTTPException(
                            status_code=400,
                            detail="At least one job search work type is required by the profile edit schema.",
                        )
                    if not existing_search_rows and search.jobSearchAnswer is None:
                        raise HTTPException(
                            status_code=400,
                            detail="jobSearchAnswer is required when initializing the job search profile.",
                        )
                    default_answer = (
                        existing_search_rows[0].job_search_profile_id if existing_search_rows else search.jobSearchAnswer
                    )
                    default_visibility = (
                        existing_search_rows[0].founders_can_see if existing_search_rows else False
                    )

                    def apply_job_search(row, work_type_id):
                        row.job_search_profile_id = search.jobSearchAnswer or row.job_search_profile_id or default_answer
                        row.job_search_profile_work_type_id = work_type_id
                        row.founders_can_see = (
                            search.foundersCanSee
                            if search.foundersCanSee is not None
                            else row.founders_can_see if row.id is not None else default_visibility
                        )

                    rows = _sync_ordered_rows(
                        db,
                        UserJobSearchProfile,
                        profile.id,
                        search.jobSearchWorkType,
                        apply_job_search,
                    )
                    talent_rows["job_search"] = rows[0]
                elif search.foundersCanSee is not None or search.jobSearchAnswer is not None:
                    if not existing_search_rows:
                        raise HTTPException(status_code=400, detail="Job search work types are required.")
                    for row in existing_search_rows:
                        if search.foundersCanSee is not None:
                            row.founders_can_see = search.foundersCanSee
                        if search.jobSearchAnswer is not None:
                            row.job_search_profile_id = search.jobSearchAnswer
                    talent_rows["job_search"] = next(
                        (row for row in existing_search_rows if row.id == current_search_id),
                        existing_search_rows[0],
                    )

            if talent.compensation:
                compensation_values = _present_values(
                    talent.compensation,
                    {
                        "cashEquityExpectation": "cash_equity_expectation_id",
                        "expectedMinimumSalary": "expected_minimum_salary_id",
                        "salaryDuration": "salary_duration_id",
                        "currency": "currency_id",
                        "amount": "annual_salary",
                    },
                )
                if "annual_salary" in compensation_values and compensation_values["annual_salary"] is not None:
                    try:
                        amount = str(compensation_values["annual_salary"]).replace(",", "").strip()
                        compensation_values["annual_salary"] = Decimal(amount)
                    except InvalidOperation as exc:
                        raise HTTPException(status_code=422, detail="amount must be a valid number.") from exc
                if compensation_values:
                    talent_rows["compensation"] = _upsert_profile_row(
                        db,
                        UserProfileCompensation,
                        profile.id,
                        current_edit_values.get("user_profile_compensation_id"),
                        compensation_values,
                    )

            if talent.workAuthorization is not None:
                talent_rows["work_authorization"] = _upsert_profile_row(
                    db,
                    UserProfileWorkAuthorization,
                    profile.id,
                    None,
                    {"work_authorization_id": talent.workAuthorization},
                )

            if talent.company_size_interest is not None:
                if not talent.company_size_interest:
                    raise HTTPException(
                        status_code=400,
                        detail="At least one company size interest is required by the profile edit schema.",
                    )

                def apply_company_size(row, item):
                    row.company_size_id = item.company_size
                    row.company_size_interest_level_id = item.interest_level

                company_size_rows = _sync_ordered_rows(
                    db,
                    UserProfileCompanySizeInterest,
                    profile.id,
                    talent.company_size_interest,
                    apply_company_size,
                )
                talent_rows["company_size"] = company_size_rows[0]

        about_rows: dict[str, Any] = {}
        if payload.userAbout:
            about = payload.userAbout
            if about.industries is not None:
                db.query(UserProfileIndustry).filter(
                    UserProfileIndustry.user_profile_id == profile.id
                ).delete(synchronize_session=False)
                for industry_id in dict.fromkeys(about.industries):
                    db.add(UserProfileIndustry(user_profile_id=profile.id, industry_id=industry_id))
            if about.priorStartupExperience is not None:
                about_rows["prior_startup"] = _upsert_profile_row(
                    db,
                    UserProfilePriorStartupExperience,
                    profile.id,
                    current_edit_values.get("user_profile_prior_startup_exp_id"),
                    {"prior_startup_experience_id": about.priorStartupExperience},
                )

        db.flush()

        def row_id_or_existing(row_key: str, row_model: Any, pointer: str) -> int | None:
            row = prompt_rows[0] if row_key == "prompt" and prompt_rows else None
            if row is None:
                row = founder_rows.get(row_key) or talent_rows.get(row_key) or about_rows.get(row_key)
            return row.id if row is not None else _resolve_profile_pointer(
                db, current_edit, pointer, row_model, profile.id
            )

        matching_goal_id = row_id_or_existing(
            "matching_goal", UserProfileMatchingGoal, "user_profile_matching_goal_id"
        )
        commitment_id = row_id_or_existing(
            "commitment", UserProfileCommitmentLevel, "user_profile_commitment_level_id"
        )
        equity_split_id = row_id_or_existing(
            "equity_split", UserProfileEquitySplit, "user_profile_equity_split_id"
        )
        prior_startup_id = row_id_or_existing(
            "prior_startup", UserProfilePriorStartupExperience, "user_profile_prior_startup_exp_id"
        )
        job_search_id = talent_rows.get("job_search")
        job_search_id = job_search_id.id if job_search_id else current_edit_values.get("user_job_search_profile_id")
        if job_search_id is None:
            existing_job_search = (
                db.query(UserJobSearchProfile)
                .filter(UserJobSearchProfile.user_profile_id == profile.id)
                .order_by(UserJobSearchProfile.id.asc())
                .first()
            )
            job_search_id = existing_job_search.id if existing_job_search is not None else None
        compensation_id = row_id_or_existing(
            "compensation", UserProfileCompensation, "user_profile_compensation_id"
        )
        company_size_id = row_id_or_existing(
            "company_size", UserProfileCompanySizeInterest, "user_profile_company_size_id"
        )
        prompt_id = prompt_rows[0].id if prompt_rows else current_edit_values.get("user_profile_prompt_id")
        if prompt_id is None:
            existing_prompt = (
                db.query(UserProfilePrompt)
                .filter(UserProfilePrompt.user_profile_id == profile.id)
                .order_by(UserProfilePrompt.display_order.asc())
                .first()
            )
            prompt_id = existing_prompt.id if existing_prompt is not None else None
        described_as_id = (
            requested_selector
            if requested_selector is not None
            else current_edit_values.get("user_described_as_id")
        )
        no_of_founders = (
            founder.noOfFounders
            if founder and "noOfFounders" in founder.model_fields_set and founder.noOfFounders is not None
            else current_edit_values.get("user_profile_no_of_founders")
        )
        headline = (
            payload.headline
            if "headline" in payload.model_fields_set
            else current_edit_values.get("user_profile_headline")
        )
        scheduling_link = (
            payload.userProfile.schedulingLink
            if payload.userProfile and "schedulingLink" in payload.userProfile.model_fields_set
            else current_edit_values.get("user_profile_scheduling_link")
        )

        required_references = {
            "user prompt": prompt_id,
            "described-as value": described_as_id,
            "prior startup experience": prior_startup_id,
        }
        if founder_active:
            required_references.update(
                {
                    "matching goal": matching_goal_id,
                    "commitment level": commitment_id,
                    "equity split": equity_split_id,
                    "number of founders": no_of_founders,
                }
            )
        if talent_active:
            required_references.update(
                {
                    "job search profile": job_search_id,
                    "compensation": compensation_id,
                    "company size interest": company_size_id,
                }
            )
        missing_references = [name for name, value in required_references.items() if value is None]
        if missing_references:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The profile edit record is incomplete. Supply values for: "
                    + ", ".join(missing_references)
                    + "."
                ),
            )

        db.add(
            UserProfileEdit(
                user_profile_id=profile.id,
                user_profile_prompt_id=prompt_id,
                user_profile_matching_goal_id=matching_goal_id,
                user_profile_commitment_level_id=commitment_id,
                user_profile_equity_split_id=equity_split_id,
                user_described_as_id=described_as_id,
                user_profile_prior_startup_exp_id=prior_startup_id,
                user_profile_scheduling_link=scheduling_link,
                user_job_search_profile_id=job_search_id,
                user_profile_compensation_id=compensation_id,
                user_profile_company_size_id=company_size_id,
                user_profile_no_of_founders=no_of_founders,
                user_profile_headline=headline,
            )
        )

        db.commit()
        return UserProfileEditResponse(
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
            detail="Invalid foreign key reference or conflicting profile value.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(exc)}",
        ) from exc
