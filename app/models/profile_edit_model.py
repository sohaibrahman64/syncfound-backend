from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import MONEY
from sqlalchemy.sql import func

from app.database import Base


class UserProfilePrompt(Base):
    __tablename__ = "user_profile_prompts"
    __table_args__ = (UniqueConstraint("user_profile_id", "display_order"),)

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    prompt_id = Column(BigInteger, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    answer = Column(Text, nullable=False)
    display_order = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class UserProfileCommitmentLevel(Base):
    __tablename__ = "user_profile_commitment_levels"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    commitment_level_id = Column(BigInteger, ForeignKey("commitment_levels.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileMatchingGoal(Base):
    __tablename__ = "user_profile_matching_goals"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    matching_goal_id = Column(BigInteger, ForeignKey("matching_goals.id"), nullable=False)
    is_hiring = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileEquitySplit(Base):
    __tablename__ = "user_profile_equity_split"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    equity_split_id = Column(BigInteger, ForeignKey("equity_split.id"), nullable=False)
    min_equity_range = Column(BigInteger, nullable=True)
    max_equity_range = Column(BigInteger, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileCompensation(Base):
    __tablename__ = "user_profile_compensation"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    cash_equity_expectation_id = Column(BigInteger, ForeignKey("cash_equity_expectations.id"), nullable=False)
    expected_minimum_salary_id = Column(BigInteger, ForeignKey("expected_minimum_salary.id"), nullable=True)
    salary_duration_id = Column(BigInteger, ForeignKey("salary_duration.id"), nullable=False)
    currency_id = Column(BigInteger, ForeignKey("currencies.currency_id"), nullable=False)
    annual_salary = Column(MONEY, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileWorkAuthorization(Base):
    __tablename__ = "user_profile_work_authorization"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    work_authorization_id = Column(BigInteger, ForeignKey("work_authorizations.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfilePriorStartupExperience(Base):
    __tablename__ = "user_profile_prior_startup_experience"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    prior_startup_experience_id = Column(BigInteger, ForeignKey("prior_startup_experiences.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileCompanySizeInterest(Base):
    __tablename__ = "user_profile_company_size_interest"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    company_size_id = Column(BigInteger, nullable=False)
    company_size_interest_level_id = Column(BigInteger, ForeignKey("company_size_interest_levels.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserJobSearchProfile(Base):
    __tablename__ = "user_job_search_profile"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=True)
    job_search_profile_id = Column(BigInteger, ForeignKey("job_search_profiles.id"), nullable=False)
    job_search_profile_work_type_id = Column(BigInteger, ForeignKey("job_search_profile_work_types.id"), nullable=False)
    founders_can_see = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileEdit(Base):
    __tablename__ = "user_profile_edit"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    user_profile_prompt_id = Column(
        BigInteger,
        ForeignKey("user_profile_prompts.id", ondelete="CASCADE", name="fk_user_profile_prompt_id"),
        nullable=False,
    )
    user_profile_matching_goal_id = Column(
        BigInteger,
        ForeignKey("user_profile_matching_goals.id", ondelete="CASCADE", name="fk_user_profile_matching_goal_id"),
        nullable=True,
    )
    user_profile_commitment_level_id = Column(
        BigInteger,
        ForeignKey("user_profile_commitment_levels.id", ondelete="CASCADE", name="fk_user_profile_commitment_level_id"),
        nullable=True,
    )
    user_profile_equity_split_id = Column(
        BigInteger,
        ForeignKey("user_profile_equity_split.id", ondelete="CASCADE", name="fk_user_profile_equity_split_id"),
        nullable=True,
    )
    user_described_as_id = Column(
        BigInteger,
        ForeignKey("user_described_as.id", ondelete="CASCADE", name="fk_user_described_as_id"),
        nullable=False,
    )
    user_profile_prior_startup_exp_id = Column(
        BigInteger,
        ForeignKey(
            "user_profile_prior_startup_experience.id",
            ondelete="CASCADE",
            name="fk_user_profile_prior_startup_exp_id",
        ),
        nullable=False,
    )
    user_profile_scheduling_link = Column(String(1000), nullable=True)
    user_job_search_profile_id = Column(
        BigInteger,
        ForeignKey("user_job_search_profile.id", ondelete="CASCADE", name="fk_user_job_search_profile_id"),
        nullable=True,
    )
    user_profile_compensation_id = Column(
        BigInteger,
        ForeignKey("user_profile_compensation.id", ondelete="CASCADE", name="fk_user_profile_compensation_id"),
        nullable=True,
    )
    user_profile_company_size_id = Column(
        BigInteger,
        ForeignKey(
            "user_profile_company_size_interest.id",
            ondelete="CASCADE",
            name="fk_user_profile_company_size_id",
        ),
        nullable=True,
    )
    user_profile_no_of_founders = Column(BigInteger, nullable=True)
    user_profile_headline = Column(String(1000), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileEditExperience(Base):
    __tablename__ = "user_profile_edit_experiences"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(1000), nullable=True)
    company = Column(String(1000), nullable=True)
    is_currently_working = Column(Boolean, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class UserProfileEditEducation(Base):
    __tablename__ = "user_profile_edit_education"

    id = Column(BigInteger, primary_key=True)
    user_profile_id = Column(BigInteger, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False)
    school = Column(String(1000), nullable=True)
    degree = Column(String(1000), nullable=True)
    field_of_study = Column(String(1000), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
