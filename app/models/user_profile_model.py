from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.cofounder_skill_model import CofounderSkill
from app.models.user_skill_model import UserSkill
from app.models.industry_model import Industry
from app.models.location_preference_model import (
    LocationPreferenceQuestion,
    LocationPreferenceAnswer,
)
from app.models.user_profile_experiences_model import UserProfileExperience
from app.models.user_profile_education_model import UserProfileEducation


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(BigInteger, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)

    date_of_birth = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)

    state_id = Column(
        Integer,
        ForeignKey("states.id"),
        nullable=True,
    )

    city_id = Column(
        Integer,
        ForeignKey("cities.id"),
        nullable=True,
    )

    matching_purpose_id = Column(
        Integer,
        ForeignKey("matching_purposes.id"),
        nullable=True,
    )

    user_role_id = Column(
        Integer,
        ForeignKey("user_roles.id"),
        nullable=True,
    )

    cofounder_role_id = Column(
        Integer,
        ForeignKey("cofounder_roles.id"),
        nullable=True,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    primary_role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=True,
    )

    secondary_role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=True,
    )

    bio = Column(Text, nullable=True)
    startup_idea = Column(Text, nullable=True)

    funding_stage_id = Column(Integer, ForeignKey("funding_stage.id", ondelete="RESTRICT"), nullable=False, index=True)
    time_commitment_id = Column(Integer, ForeignKey("time_commitment.id", ondelete="RESTRICT"), nullable=False, index=True)
    risk_appetite_id = Column(Integer, ForeignKey("risk_appetite.id", ondelete="RESTRICT"), nullable=False, index=True)
    employment_type_id = Column(Integer, ForeignKey("employment_types.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Other existing profile-level columns remain here.

    headline = Column(
        String(500),
        nullable=True,
    )

    founder_count = Column(
        Integer,  # Using Integer instead of SmallInteger for broader compatibility
        nullable=True,
    )

    prior_startup_experience_id = Column(
        Integer,
        ForeignKey("prior_startup_experiences.id"),
        nullable=True,
    )

    work_authorization_id = Column(
        Integer,
        ForeignKey("work_authorizations.id"),
        nullable=True,
    )

    linkedin_profile_id = Column(
        BigInteger,
        ForeignKey("linkedin_profiles.id"),
        nullable=True,
    )

    linkedin_url = Column(
        String(500),
        nullable=True,
    )

    linkedin_username = Column(
        String(255),
        nullable=True,
    )

    # LinkedIn preview fields
    linkedin_profile_preview_headline = Column(
        Text,
        nullable=True,
    )

    linkedin_profile_preview_first_organization = Column(
        String(255),
        nullable=True,
    )

    linkedin_profile_preview_first_education_institution = Column(
        String(255),
        nullable=True,
    )

    linkedin_profile_preview_first_location = Column(
        String(255),
        nullable=True,
    )

    linkedin_profile_preview_connections = Column(
        Integer,
        nullable=True,
    )

    # Profile image fields
    linkedin_profile_picture_url = Column(
        Text,
        nullable=True,
    )

    pending_profile_image_uri = Column(
        Text,
        nullable=True,
    )

    pending_profile_image_source = Column(
        String(50),
        nullable=True,
    )

    profile_image_rotation = Column(
        Float,
        nullable=True,
    )

    profile_image_scale = Column(
        Float,
        nullable=True,
    )

    profile_image_translate_x = Column(
        Float,
        nullable=True,
    )

    profile_image_translate_y = Column(
        Float,
        nullable=True,
    )

    profile_image_crop_x = Column(
        Float,
        nullable=True,
    )

    profile_image_crop_y = Column(
        Float,
        nullable=True,
    )

    profile_image_crop_width = Column(
        Float,
        nullable=True,
    )

    profile_image_crop_height = Column(
        Float,
        nullable=True,
    )

    profile_image_uri = Column(
        Text,
        nullable=True,
    )

    profile_image_source = Column(
        String(50),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    experiences = relationship(
        "UserProfileExperience",
        back_populates="user_profile",
        cascade="all, delete-orphan",
        order_by="UserProfileExperience.display_order",
    )

    education = relationship(
        "UserProfileEducation",
        back_populates="user_profile",
        cascade="all, delete-orphan",
        order_by="UserProfileEducation.display_order",
    )

    prompts = relationship(
        "UserProfilePrompt",
        back_populates="user_profile",
        cascade="all, delete-orphan",
        order_by="UserProfilePrompt.display_order",
    )

    compensation = relationship(
        "UserProfileCompensation",
        back_populates="user_profile",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # User skills relationship
    user_skills = relationship(
        "UserProfileUserSkill",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )

    # Cofounder skills relationship
    cofounder_skills = relationship(
        "UserProfileCofounderSkill",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )

    # Industry relationships
    industries = relationship(
        "UserProfileIndustry",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )

    # Location preferences relationship
    location_preferences = relationship(
        "UserProfileLocationPreference",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )


class UserProfileUserSkill(Base):
    __tablename__ = "user_profile_user_skills"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign key to user profile
    user_profile_id = Column(
        BigInteger,
        ForeignKey("user_profile.id"),
        nullable=False,
    )

    # Foreign key to user skill
    skill_id = Column(
        Integer,
        ForeignKey("user_skills.id"),
        nullable=False,
    )

    # Relationships
    user_profile = relationship(
        "UserProfile",
        back_populates="user_skills",
    )
    skill = relationship(
        "UserSkill",
    )


class UserProfileCofounderSkill(Base):
    __tablename__ = "user_profile_cofounder_skills"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign key to user profile
    user_profile_id = Column(
        BigInteger,
        ForeignKey("user_profile.id"),
        nullable=False,
    )

    # Foreign key to cofounder skill
    skill_id = Column(
        Integer,
        ForeignKey("cofounder_skills.id"),
        nullable=False,
    )

    # Relationships
    user_profile = relationship(
        "UserProfile",
        back_populates="cofounder_skills",
    )
    skill = relationship(
        "CofounderSkill",
    )


class UserProfileIndustry(Base):
    __tablename__ = "user_profile_industries"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign key to user profile
    user_profile_id = Column(
        BigInteger,
        ForeignKey("user_profile.id"),
        nullable=False,
    )

    # Foreign key to industry
    industry_id = Column(
        Integer,
        ForeignKey("industries.id"),
        nullable=False,
    )

    # Relationships
    user_profile = relationship(
        "UserProfile",
        back_populates="industries",
    )
    industry = relationship(
        "Industry",
    )


class UserProfileLocationPreference(Base):
    __tablename__ = "user_profile_location_preferences"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Foreign key to user profile
    user_profile_id = Column(
        BigInteger,
        ForeignKey("user_profile.id"),
        nullable=False,
    )

    # Foreign key to location preference question
    question_id = Column(
        Integer,
        ForeignKey("location_preference_questions.id"),
        nullable=False,
    )

    # Foreign key to location preference answer
    selected_answer_id = Column(
        Integer,
        ForeignKey("location_preference_answers.id"),
        nullable=False,
    )

    # Relationships
    user_profile = relationship(
        "UserProfile",
        back_populates="location_preferences",
    )
    question = relationship(
        "LocationPreferenceQuestion",
    )
    selected_answer = relationship(
        "LocationPreferenceAnswer",
    )