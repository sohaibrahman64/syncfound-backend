from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.sql import func

from app.database import Base


class PriorStartupExperience(Base):
    __tablename__ = "prior_startup_experiences"

    id = Column(BIGINT, primary_key=True, index=True)
    prior_startup_experience = Column(String(1000), nullable=False)
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