from sqlalchemy import Boolean, BigInteger, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class LinkedInProfile(Base):
    __tablename__ = "linkedin_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_linkedin_profiles_user_id"),
        UniqueConstraint("public_identifier", name="uq_linkedin_profiles_public_identifier"),
        UniqueConstraint("profile_url", name="uq_linkedin_profiles_profile_url"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    fullname = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    headline = Column(Text, nullable=True)
    public_identifier = Column(String(255), nullable=False, index=True)
    profile_url = Column(Text, nullable=False)
    profile_picture_url = Column(Text, nullable=True)
    about = Column(Text, nullable=True)

    location_country = Column(String(255), nullable=True)
    location_city = Column(String(255), nullable=True)
    location_full = Column(String(255), nullable=True)
    location_postal_code = Column(String(50), nullable=True)
    location_country_code = Column(String(10), nullable=True)

    is_creator = Column(Boolean, nullable=True)
    is_influencer = Column(Boolean, nullable=True)
    is_premium = Column(Boolean, nullable=True)
    open_to_work = Column(Boolean, nullable=True)
    created_timestamp_ms = Column(BigInteger, nullable=True)
    show_follower_count = Column(Boolean, nullable=True)
    background_picture_url = Column(Text, nullable=True)
    memorialized = Column(Boolean, nullable=True)
    is_top_voice = Column(Boolean, nullable=True)
    primary_locale = Column(String(50), nullable=True)
    urn = Column(String(255), nullable=True)
    follower_count = Column(Integer, nullable=True)
    connection_count = Column(Integer, nullable=True)

    top_education_school_name = Column(String(255), nullable=True)
    top_education_school_urn = Column(String(255), nullable=True)
    top_education_school_url = Column(Text, nullable=True)
    top_education_school_logo_url = Column(Text, nullable=True)

    current_company = Column(String(255), nullable=True)
    current_company_urn = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LinkedInProfileCreatorHashtag(Base):
    __tablename__ = "linkedin_profile_creator_hashtags"
    __table_args__ = (
        UniqueConstraint("profile_id", "hashtag", name="uq_linkedin_profile_creator_hashtags_profile_hashtag"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    hashtag = Column(String(255), nullable=False)


class LinkedInProfileTopSkill(Base):
    __tablename__ = "linkedin_profile_top_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "skill", name="uq_linkedin_profile_top_skills_profile_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = Column(String(255), nullable=False)


class LinkedInProfileExperience(Base):
    __tablename__ = "linkedin_profile_experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    duration = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    start_month = Column(String(20), nullable=True)
    end_year = Column(Integer, nullable=True)
    end_month = Column(String(20), nullable=True)
    is_current = Column(Boolean, nullable=True)
    company_linkedin_url = Column(Text, nullable=True)
    company_logo_url = Column(Text, nullable=True)
    employment_type = Column(String(100), nullable=True)
    location_type = Column(String(100), nullable=True)
    company_id = Column(String(100), nullable=True)
    skills_url = Column(Text, nullable=True)


class LinkedInProfileExperienceSkill(Base):
    __tablename__ = "linkedin_profile_experience_skills"
    __table_args__ = (
        UniqueConstraint("experience_id", "skill", name="uq_linkedin_profile_experience_skills_experience_skill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    experience_id = Column(Integer, ForeignKey("linkedin_profile_experiences.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = Column(String(255), nullable=False)


class LinkedInProfileEducation(Base):
    __tablename__ = "linkedin_profile_education"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    school = Column(String(255), nullable=True)
    degree = Column(Text, nullable=True)
    degree_name = Column(String(255), nullable=True)
    field_of_study = Column(String(255), nullable=True)
    duration = Column(String(255), nullable=True)
    school_linkedin_url = Column(Text, nullable=True)
    start_year = Column(Integer, nullable=True)
    start_month = Column(String(20), nullable=True)
    end_year = Column(Integer, nullable=True)
    end_month = Column(String(20), nullable=True)


class LinkedInProfileProject(Base):
    __tablename__ = "linkedin_profile_projects"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_current = Column(Boolean, nullable=True)


class LinkedInProfileCertification(Base):
    __tablename__ = "linkedin_profile_certifications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=True)
    issuer = Column(String(255), nullable=True)
    issued_date = Column(String(255), nullable=True)


class LinkedInProfileLanguage(Base):
    __tablename__ = "linkedin_profile_languages"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    language = Column(String(255), nullable=True)
    proficiency = Column(String(255), nullable=True)


class LinkedInProfileCourse(Base):
    __tablename__ = "linkedin_profile_courses"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=True)


class LinkedInProfileCause(Base):
    __tablename__ = "linkedin_profile_causes"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("linkedin_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    cause = Column(String(255), nullable=False)