from sqlalchemy import Column, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.sql import func

from app.database import Base


class UserDescribedAs(Base):
    __tablename__ = "user_described_as"

    id = Column(BIGINT, primary_key=True, index=True)
    described_as = Column(String(1000), nullable=False)
    icon = Column(String(500), nullable=True)
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