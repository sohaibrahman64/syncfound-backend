from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profile"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profile_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    age = Column(Integer, nullable=True)

    state_id = Column(Integer, ForeignKey("states.id", ondelete="RESTRICT"), nullable=False, index=True)
    city_id = Column(Integer, ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)

    matching_purpose_id = Column(Integer, ForeignKey("matching_purpose.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_role_id = Column(Integer, ForeignKey("user_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    cofounder_role_id = Column(Integer, ForeignKey("cofounder_roles.id", ondelete="RESTRICT"), nullable=False, index=True)

    title = Column(String(255), nullable=True)
    primary_role_id = Column(Integer, ForeignKey("primary_role.id", ondelete="RESTRICT"), nullable=False, index=True)
    secondary_role_id = Column(Integer, ForeignKey("secondary_role.id", ondelete="RESTRICT"), nullable=True, index=True)

    bio = Column(Text, nullable=True)
    startup_idea = Column(Text, nullable=True)

    funding_stage_id = Column(Integer, ForeignKey("funding_stage.id", ondelete="RESTRICT"), nullable=False, index=True)
    time_commitment_id = Column(Integer, ForeignKey("time_commitment.id", ondelete="RESTRICT"), nullable=False, index=True)
    risk_appetite_id = Column(Integer, ForeignKey("risk_appetite.id", ondelete="RESTRICT"), nullable=False, index=True)
    employment_type_id = Column(Integer, ForeignKey("employment_types.id", ondelete="RESTRICT"), nullable=False, index=True)

    company_name = Column(String(255), nullable=True)
    experience_location = Column(String(255), nullable=True)
    location_type_id = Column(Integer, ForeignKey("location_types.id", ondelete="RESTRICT"), nullable=True, index=True)

    start_date = Column(DateTime(timezone=True), nullable=True)
    currently_work_here = Column(Boolean, nullable=False, default=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    linkedin_url = Column(Text, nullable=True)
    linkedin_username = Column(String(255), nullable=True)

    linkedin_profile_preview_headline = Column(Text, nullable=True)
    linkedin_profile_preview_first_organization = Column(String(255), nullable=True)
    linkedin_profile_preview_first_education_institution = Column(String(255), nullable=True)
    linkedin_profile_preview_first_location = Column(String(255), nullable=True)
    linkedin_profile_preview_connections = Column(String(255), nullable=True)

    linkedin_profile_picture_url = Column(Text, nullable=True)
    pending_profile_image_uri = Column(Text, nullable=True)
    pending_profile_image_source = Column(String(50), nullable=True)

    profile_image_rotation = Column(Float, nullable=False, default=0)
    profile_image_scale = Column(Float, nullable=False, default=1)
    profile_image_translate_x = Column(Float, nullable=False, default=0)
    profile_image_translate_y = Column(Float, nullable=False, default=0)

    profile_image_crop_x = Column(Float, nullable=True)
    profile_image_crop_y = Column(Float, nullable=True)
    profile_image_crop_width = Column(Float, nullable=True)
    profile_image_crop_height = Column(Float, nullable=True)

    profile_image_uri = Column(Text, nullable=True)
    profile_image_source = Column(String(50), nullable=True)

    linkedin_profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    location_preferences = relationship(
        "UserProfileLocationPreference",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    user_skills = relationship(
        "UserProfileUserSkill",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    cofounder_skills = relationship(
        "UserProfileCofounderSkill",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )
    industries = relationship(
        "UserProfileIndustry",
        back_populates="user_profile",
        cascade="all, delete-orphan",
    )


class UserProfileLocationPreference(Base):
    __tablename__ = "user_profile_location_preferences"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "question_id", name="uq_user_profile_location_preferences_profile_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("location_preference_questions.id", ondelete="RESTRICT"), nullable=False, index=True)
    selected_answer_id = Column(Integer, ForeignKey("location_preference_answers.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user_profile = relationship("UserProfile", back_populates="location_preferences")


class UserProfileUserSkill(Base):
    __tablename__ = "user_profile_user_skills"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "skill_id", name="uq_user_profile_user_skills_profile_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("user_skills.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user_profile = relationship("UserProfile", back_populates="user_skills")


class UserProfileCofounderSkill(Base):
    __tablename__ = "user_profile_cofounder_skills"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "skill_id", name="uq_user_profile_cofounder_skills_profile_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("cofounder_skills.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user_profile = relationship("UserProfile", back_populates="cofounder_skills")


class UserProfileIndustry(Base):
    __tablename__ = "user_profile_industries"
    __table_args__ = (
        UniqueConstraint("user_profile_id", "industry_id", name="uq_user_profile_industries_profile_industry"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_profile_id = Column(Integer, ForeignKey("user_profile.id", ondelete="CASCADE"), nullable=False, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    user_profile = relationship("UserProfile", back_populates="industries")