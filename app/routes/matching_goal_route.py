from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.matching_goal_model import MatchingGoal
from app.schemas.matching_goal_schema import MatchingGoalResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Matching Goals"]
)

@router.get("/matching-goals", response_model=List[MatchingGoalResponse])
def get_matching_goals(db: Session = Depends(get_db)):
    matching_goals = db.query(MatchingGoal).order_by(MatchingGoal.matching_goal.asc()).all()
    return matching_goals