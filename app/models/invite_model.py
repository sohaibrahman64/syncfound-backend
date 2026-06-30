from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database import Base


class Invite(Base):
    __tablename__ = "invites"
    __table_args__ = (
        CheckConstraint("sender_user_id <> recipient_user_id", name="chk_invites_not_self"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'withdrawn', 'expired')",
            name="chk_invites_status",
        ),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    public_id = Column(String(40), nullable=False, unique=True, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_match_action_id = Column(Integer, ForeignKey("match_actions.id", ondelete="SET NULL"), nullable=True, index=True)
    source_request_id = Column(String(36), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    read_at = Column(TIMESTAMP(timezone=True), nullable=True)
    responded_at = Column(TIMESTAMP(timezone=True), nullable=True)
    mutual_match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True, index=True)
    withdrawn_at = Column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
