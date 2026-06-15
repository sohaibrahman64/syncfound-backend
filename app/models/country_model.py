import datetime

from sqlalchemy import create_engine # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean # type: ignore
from sqlalchemy.sql import func
from app.database import Base

class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    country_name = Column(String, unique=True, index=True)
    country_code = Column(String, unique=True, index=True)
    country_iso = Column(String, unique=True, index=True)
    country_flag_path = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())