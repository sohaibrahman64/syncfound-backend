from sqlalchemy import Column, Integer, String  # type: ignore

from app.database import Base


class MatchingPurpose(Base):
    __tablename__ = "matching_purpose"

    id = Column(Integer, primary_key=True, index=True)
    matching_purpose = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    icon = Column(String(255), nullable=True)
    selected_icon = Column(String(255), nullable=True)
