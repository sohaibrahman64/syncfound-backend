from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint  # type: ignore
from sqlalchemy.sql import func

from app.database import Base


class State(Base):
    __tablename__ = "states"
    __table_args__ = (
        UniqueConstraint("country_id", "state_name", name="uq_states_country_name"),
        UniqueConstraint("country_id", "state_code", name="uq_states_country_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False, index=True)
    state_name = Column(String(120), nullable=False)
    state_code = Column(String(20), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )