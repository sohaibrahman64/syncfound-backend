from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('invite.created', 'invite.accepted', 'invite.declined', 'invite.withdrawn')",
            name="chk_notification_outbox_event_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'dead')",
            name="chk_notification_outbox_status",
        ),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    event_id = Column(String(36), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    invite_id = Column(BigInteger, ForeignKey("invites.id", ondelete="CASCADE"), nullable=True, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
