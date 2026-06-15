from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint  # type: ignore
from sqlalchemy.sql import func

from app.database import Base


class City(Base):
    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("country_id", "city_name", name="uq_cities_country_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries_new.id", ondelete="RESTRICT"), nullable=False, index=True)
    city_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
