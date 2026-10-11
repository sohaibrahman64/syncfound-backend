from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.prompt_model import Prompt
from app.schemas.prompt_schema import Prompt as PromptSchema

router = APIRouter(
    prefix="/api/v1",
    tags=["Prompts"],
)


@router.get("/prompts", response_model=List[PromptSchema])
def get_prompts(
    db: Session = Depends(get_db),
):
    """
    Retrieve prompts.
    """
    prompts = db.query(Prompt).all()
    return prompts


@router.get("/prompts/{prompt_id}", response_model=PromptSchema)
def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a specific prompt by ID.
    """
    prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if prompt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prompt not found",
        )
    return prompt