import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class JobMatchResponse(BaseModel):
    """Detailed explainable job-to-resume match breakdown."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    job_title: str
    company_name: str
    overall_match_score: float = Field(..., description="Overall compatibility percentage (0.0 to 100.0%)")
    skill_score: float = Field(..., description="Skill alignment percentage (0.0 to 100.0%)")
    experience_score: float = Field(..., description="Years of experience alignment percentage (0.0 to 100.0%)")
    semantic_score: float = Field(..., description="Content and domain relevance score (0.0 to 100.0%)")
    matched_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    explanation_summary: str
    job_url: Optional[str] = None
    source_email_id: Optional[uuid.UUID] = None
    created_at: datetime


class MatchListResponse(BaseModel):
    """Paginated list of job matches."""
    items: List[JobMatchResponse]
    total: int
    skip: int
    limit: int


class BatchMatchResponse(BaseModel):
    """Summary of batch matching execution across all active candidate jobs."""
    total_jobs_evaluated: int
    total_matches_created: int
    average_match_score: float
    high_match_count: int = Field(..., description="Number of jobs scoring 70.0% or above")
    message: str
