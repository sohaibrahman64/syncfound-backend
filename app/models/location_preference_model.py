from sqlalchemy import Column, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class LocationPreferenceQuestion(Base):
    __tablename__ = "location_preference_questions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    answers = relationship("LocationPreferenceAnswer", back_populates="question", order_by="LocationPreferenceAnswer.id")


class LocationPreferenceAnswer(Base):
    __tablename__ = "location_preference_answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("location_preference_questions.id"), nullable=False, index=True)
    answer = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    question = relationship("LocationPreferenceQuestion", back_populates="answers")
