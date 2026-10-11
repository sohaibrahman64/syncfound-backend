from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_search_profile_model import JobSearchProfile, JobSearchProfileWorkType
from app.schemas.job_search_profile_schema import JobSearchProfileCombinedResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["Job Search Profile"]
)


@router.get("/job_search_profile", response_model=JobSearchProfileCombinedResponse)
def get_job_search_profile(db: Session = Depends(get_db)):
    job_search_profiles = db.query(JobSearchProfile).order_by(JobSearchProfile.id.asc()).all()
    job_search_profile_work_types = db.query(JobSearchProfileWorkType).order_by(JobSearchProfileWorkType.id.asc()).all()

    return JobSearchProfileCombinedResponse(
        job_search_profiles=job_search_profiles,
        job_search_profile_work_types=job_search_profile_work_types
    )