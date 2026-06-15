from sqlalchemy import Boolean, Column, Integer, String, TIMESTAMP  # type: ignore
from sqlalchemy.sql import func

from app.database import Base


class CountryNew(Base):
    __tablename__ = "countries_new"

    id = Column(Integer, primary_key=True, index=True)
    country_name = Column(String(255), nullable=False, index=True)
    iso2 = Column(String(2), unique=True, index=True, nullable=False)
    iso3 = Column(String(3), unique=True, index=True, nullable=True)
    phone_code = Column(String(20), nullable=True)
    capital = Column(String(255), nullable=True)
    currency = Column(String(20), nullable=True)
    native_name = Column(String(255), nullable=True)
    emoji = Column(String(20), nullable=True)
    emoji_u = Column(String(50), nullable=True)
    country_flag_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )