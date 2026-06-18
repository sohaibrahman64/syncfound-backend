from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint, CheckConstraint
from sqlalchemy.sql import func

from app.database import Base


class MatchAction(Base):
    __tablename__ = "match_actions"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("action IN ('like', 'pass', 'save')", name="chk_match_actions_action"),
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_matches_user_pair"),
        CheckConstraint("user_a_id < user_b_id", name="chk_matches_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user_b_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
