from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserProfileCompensation(Base):
    __tablename__ = "user_profile_compensation"

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
        unique=True,
        index=True,
    )

    cash_equity_expectation_id = Column(
        BigInteger,
        ForeignKey(
            "cash_equity_expectations.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    expected_minimum_salary_id = Column(
        BigInteger,
        ForeignKey(
            "expected_minimum_salary.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    salary_duration_id = Column(
        BigInteger,
        ForeignKey(
            "salary_duration.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    currency_id = Column(
        Integer,
        ForeignKey(
            "currencies.currency_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    expected_salary_amount = Column(
        Numeric(15, 2),
        nullable=True,
    )

    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to user profile
    user_profile = relationship(
        "UserProfile",
        back_populates="compensation",
    )