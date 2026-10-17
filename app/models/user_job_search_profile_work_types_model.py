from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserJobSearchProfileWorkType(Base):
    __tablename__ = "user_job_search_profile_work_types"

    user_job_search_profile_id = Column(
        BigInteger,
        ForeignKey(
            "user_job_search_profile.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    work_type_id = Column(
        BigInteger,
        ForeignKey(
            "job_search_profile_work_types.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    created_at = Column(
        TIMESTAMP,
        nullable=False,
        server_default=func.now(),
    )