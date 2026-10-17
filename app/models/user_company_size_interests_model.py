from sqlalchemy import (
    Column,
    ForeignKey,
    BigInteger,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserCompanySizeInterest(Base):
    __tablename__ = "user_company_size_interests"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "company_size_id",
            name="uq_user_company_size_interest",
        ),
    )

    id = Column(
        BigInteger,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        BigInteger,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    company_size_id = Column(
        BigInteger,
        ForeignKey(
            "company_sizes.id",
        ),
        nullable=False,
        index=True,
    )

    company_level_interest_id = Column(
        BigInteger,
        ForeignKey(
            "company_size_interest_levels.id",
        ),
        nullable=False,
        index=True,
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