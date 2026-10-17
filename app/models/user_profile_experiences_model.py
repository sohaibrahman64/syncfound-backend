from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    BigInteger,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserProfileExperience(Base):
    __tablename__ = "user_profile_experiences"

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL "
            "OR start_date IS NULL "
            "OR end_date >= start_date",
            name="chk_user_profile_experiences_dates",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="chk_user_profile_experiences_order",
        ),
    )

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
    )

    user_profile_id = Column(
        BigInteger,
        ForeignKey(
            "user_profile.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    linkedin_experience_id = Column(
        BigInteger,
        ForeignKey(
            "linkedin_profile_experiences.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    company_name = Column(
        String(255),
        nullable=True,
    )

    location = Column(
        String(255),
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    start_date = Column(
        # PostgreSQL DATE
        __import__("sqlalchemy").Date,
        nullable=True,
    )

    end_date = Column(
        __import__("sqlalchemy").Date,
        nullable=True,
    )

    currently_work_here = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    employment_type_id = Column(
        Integer,
        ForeignKey(
            "employment_types.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    location_type_id = Column(
        Integer,
        ForeignKey(
            "location_types.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    display_order = Column(
        SmallInteger,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to user profile
    user_profile = relationship(
        "UserProfile",
        back_populates="experiences",
    )