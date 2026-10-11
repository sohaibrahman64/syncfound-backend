import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class JobSearchProfile(Base):
    __tablename__ = "job_search_profiles"

    id = Column(Integer, primary_key=True, index=True)
    job_search_profile = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class JobSearchProfileWorkType(Base):
    __tablename__ = "job_search_profile_work_types"

    id = Column(Integer, primary_key=True, index=True)
    job_search_profile_work_type = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())