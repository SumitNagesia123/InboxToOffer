import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    APPLIED = "APPLIED"
    NOT_APPLIED = "NOT_APPLIED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFER = "OFFER"
    WITHDRAWN = "WITHDRAWN"


class ApplicationJobSummary(BaseModel):
    """Condensed job details embedded in application responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_name: str
    title: str
    location: Optional[str] = None
    work_mode: str = "UNKNOWN"
    employment_type: str = "FULL_TIME"
    salary_currency: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    job_url: Optional[str] = None
    platform_source: str = "OTHER"


class ApplicationCreate(BaseModel):
    """Schema for tracking a new job application."""
    job_id: uuid.UUID = Field(..., description="ID of the job being tracked")
    status: ApplicationStatus = Field(ApplicationStatus.APPLIED, description="Initial pipeline status")
    applied_date: Optional[datetime] = Field(None, description="Date and time when application was submitted")
    notes: Optional[str] = Field(None, description="Candidate private notes regarding this application")


class ApplicationUpdate(BaseModel):
    """Schema for updating an existing job application status or details."""
    status: Optional[ApplicationStatus] = Field(None, description="Updated pipeline stage")
    applied_date: Optional[datetime] = Field(None, description="Updated application submission date")
    notes: Optional[str] = Field(None, description="Updated notes")


class ApplicationResponse(BaseModel):
    """Public job application representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    applied_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    job: Optional[ApplicationJobSummary] = None
    match_score: Optional[float] = Field(None, description="Match score from job_matches if computed")


class ApplicationListResponse(BaseModel):
    """Paginated list of job applications."""
    items: List[ApplicationResponse]
    total: int
    skip: int
    limit: int


class PipelineSummaryResponse(BaseModel):
    """Summary metrics of the candidate's application pipeline for Kanban and analytics."""
    total_applications: int = Field(..., description="Total tracked applications across all stages")
    stage_counts: Dict[str, int] = Field(
        ...,
        description="Number of applications per stage (DISCOVERED, APPLIED, INTERVIEWING, REJECTED, OFFER, WITHDRAWN)",
    )
    active_count: int = Field(..., description="Applications currently active (APPLIED, INTERVIEWING, OFFER)")
    interview_rate_percentage: float = Field(..., description="Ratio of interviewing applications to applied applications")
    offer_rate_percentage: float = Field(..., description="Ratio of offers to applied applications")
