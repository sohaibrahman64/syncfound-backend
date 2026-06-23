from sqlalchemy import Column, ForeignKey, Integer, Text, TIMESTAMP, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base


class MatchConnectionMessage(Base):
    __tablename__ = "match_connection_messages"
    __table_args__ = (
        CheckConstraint("from_user_id <> to_user_id", name="chk_match_connection_messages_not_self"),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    match_action_id = Column(Integer, ForeignKey("match_actions.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
