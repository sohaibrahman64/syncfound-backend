import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class CompanySizeInterestLevel(Base):
    __tablename__ = "company_size_interest_levels"

    id = Column(Integer, primary_key=True, index=True)
    company_size_interest_level = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())