from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class UserDeviceToken(Base):
    __tablename__ = "user_device_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_user_device_tokens_token"),
        CheckConstraint("provider IN ('fcm', 'apns')", name="chk_user_device_tokens_provider"),
        CheckConstraint("platform IN ('android', 'ios', 'web')", name="chk_user_device_tokens_platform"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    token = Column(String(512), nullable=False)
    platform = Column(String(20), nullable=False)
    app_version = Column(String(40), nullable=True)
    device_id = Column(String(128), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
