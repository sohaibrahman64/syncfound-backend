from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    BigInteger,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserProfileEducation(Base):
    __tablename__ = "user_profile_education"

    __table_args__ = (
        CheckConstraint(
            "end_date IS NULL "
            "OR start_date IS NULL "
            "OR end_date >= start_date",
            name="chk_user_profile_education_dates",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="chk_user_profile_education_order",
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

    linkedin_education_id = Column(
        BigInteger,
        ForeignKey(
            "linkedin_profile_education.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    institution_name = Column(
        String(255),
        nullable=True,
    )

    degree = Column(
        String(255),
        nullable=True,
    )

    field_of_study = Column(
        String(255),
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    start_date = Column(
        Date,
        nullable=True,
    )

    end_date = Column(
        Date,
        nullable=True,
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
        back_populates="education",
    )