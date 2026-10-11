from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class JobSearchProfileBase(BaseModel):
    job_search_profile: str

class JobSearchProfileCreate(JobSearchProfileBase):
    pass

class JobSearchProfileResponse(JobSearchProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobSearchProfileWorkTypeBase(BaseModel):
    job_search_profile_work_type: str

class JobSearchProfileWorkTypeCreate(JobSearchProfileWorkTypeBase):
    pass

class JobSearchProfileWorkTypeResponse(JobSearchProfileWorkTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobSearchProfileCombinedResponse(BaseModel):
    job_search_profiles: list[JobSearchProfileResponse]
    job_search_profile_work_types: list[JobSearchProfileWorkTypeResponse]