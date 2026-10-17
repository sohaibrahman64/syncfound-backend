from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.database import Base


class UserProfilePrompt(Base):
    __tablename__ = "user_profile_prompts"

    __table_args__ = (
        UniqueConstraint(
            "user_profile_id",
            "display_order",
            name="uq_user_profile_prompts_order",
        ),
        CheckConstraint(
            "display_order > 0",
            name="chk_user_profile_prompts_order",
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

    prompt_id = Column(
        Integer,
        ForeignKey(
            "prompts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    answer = Column(
        Text,
        nullable=False,
    )

    display_order = Column(
        SmallInteger,
        nullable=False,
        default=1,
        server_default="1",
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
        back_populates="prompts",
    )