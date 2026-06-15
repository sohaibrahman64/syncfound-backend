from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP  # type: ignore
from sqlalchemy.sql import func

from app.database import Base


class StateSyncCheckpoint(Base):
    __tablename__ = "state_sync_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    country_new_id = Column(Integer, ForeignKey("countries_new.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    iso2 = Column(String(2), nullable=False, index=True)
    sync_status = Column(String(20), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(String(500), nullable=True)
    last_attempt_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_success_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )