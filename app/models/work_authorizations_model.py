from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class WorkAuthorization(Base):
    __tablename__ = "work_authorizations"

    id = Column(Integer, primary_key=True, index=True)
    work_authorization = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())