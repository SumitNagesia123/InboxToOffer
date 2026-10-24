import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class WorkMode(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    UNKNOWN = "UNKNOWN"


class ExtractedJobData(BaseModel):
    """Structured job information extracted from an email."""
    company_name: str = Field(..., description="Name of hiring organization")
    title: str = Field(..., description="Job role or title")
    location: Optional[str] = Field(None, description="City, country, or location description")
    work_mode: WorkMode = Field(WorkMode.UNKNOWN, description="Work location modality")
    employment_type: EmploymentType = Field(EmploymentType.UNKNOWN, description="Type of employment")
    salary_currency: Optional[str] = Field(None, description="Salary currency e.g. USD, EUR, INR")
    salary_min: Optional[float] = Field(None, description="Minimum salary figure if explicitly mentioned")
    salary_max: Optional[float] = Field(None, description="Maximum salary figure if explicitly mentioned")
    min_experience_years: Optional[int] = Field(None, description="Minimum required years of experience")
    max_experience_years: Optional[int] = Field(None, description="Maximum experience limit if specified")
    required_skills: List[str] = Field(default_factory=list, description="Must-have technical and professional skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or preferred skills")
    job_description: Optional[str] = Field(None, description="Extracted clean job description")
    job_url: Optional[str] = Field(None, description="Direct URL to apply for the position")
    platform_source: str = Field("OTHER", description="Detected job source/portal e.g. LinkedIn, Indeed")
    application_deadline: Optional[datetime] = Field(None, description="Application closing deadline if stated")


class JobSkillResponse(BaseModel):
    """Skill linked to a job."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    is_required: bool


class JobResponse(BaseModel):
    """Public job representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    source_email_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    company_name: str
    title: str
    normalized_title: str
    location: Optional[str] = None
    work_mode: str
    employment_type: str
    salary_currency: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    min_experience_years: Optional[int] = None
    max_experience_years: Optional[int] = None
    job_description: Optional[str] = None
    job_url: Optional[str] = None
    platform_source: str
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    is_duplicate: bool
    canonical_job_id: Optional[uuid.UUID] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    created_at: datetime


class JobListResponse(BaseModel):
    """Paginated list of jobs."""
    items: List[JobResponse]
    total: int
    skip: int
    limit: int


class BatchExtractionResponse(BaseModel):
    """Summary of batch job extraction operation."""
    total_processed: int
    jobs_extracted: int
    message: str


class DuplicateMatchDetail(BaseModel):
    """Result of duplicate check analysis for a job."""
    is_duplicate: bool
    confidence: float
    match_method: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    canonical_job_id: Optional[uuid.UUID] = None


class BatchDeduplicationResponse(BaseModel):
    """Summary of batch deduplication sweep."""
    total_jobs: int
    duplicates_identified: int
    unique_canonical_jobs: int
    message: str


class DuplicateGroupResponse(BaseModel):
    """A canonical job alongside its clustered duplicate postings."""
    canonical_job: JobResponse
    duplicate_jobs: List[JobResponse]
    duplicate_count: int
