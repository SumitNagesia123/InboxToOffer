import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DashboardOverviewKPIs(BaseModel):
    """High-level performance and intelligence metrics."""
    total_emails_ingested: int = Field(..., description="Total raw emails synchronized")
    total_jobs_discovered: int = Field(..., description="Total structured job postings extracted")
    unique_jobs_count: int = Field(..., description="Canonical distinct job postings")
    duplicate_jobs_count: int = Field(..., description="Redundant cross-platform duplicates identified")
    duplicate_rate_percentage: float = Field(..., description="Percentage of jobs detected as duplicates")
    high_match_jobs_count: int = Field(..., description="Number of positions scoring 70.0% compatibility or higher")
    average_match_score: float = Field(..., description="Mean compatibility score across all non-duplicate jobs")
    total_applications: int = Field(..., description="Total applications tracked in pipeline")
    active_applications: int = Field(..., description="Applications currently in APPLIED, INTERVIEWING, or OFFER stages")
    interview_rate_percentage: float = Field(..., description="Percentage of applied jobs progressing to interview")
    offer_rate_percentage: float = Field(..., description="Percentage of applied jobs resulting in offers")


class StatusDistribution(BaseModel):
    """Distribution of applications by stage."""
    status: str
    count: int
    percentage: float


class WorkModeDistribution(BaseModel):
    """Distribution of jobs by work mode modality."""
    work_mode: str
    count: int
    percentage: float


class PlatformSourceDistribution(BaseModel):
    """Distribution of job discovery by portal source."""
    platform_source: str
    count: int
    percentage: float


class TopInDemandSkill(BaseModel):
    """Skill demand analytics with candidate possession flag."""
    name: str
    category: Optional[str] = "General"
    demand_count: int
    candidate_has_skill: bool


class ScoreBucket(BaseModel):
    """Job compatibility match score histogram bucket."""
    range_label: str
    count: int
    percentage: float


class ActivityItem(BaseModel):
    """Timeline entry representing recent system activity."""
    id: uuid.UUID
    activity_type: str  # EMAIL, JOB, APPLICATION, DIGEST, NOTIFICATION
    title: str
    description: str
    timestamp: datetime


class DashboardAnalyticsResponse(BaseModel):
    """Complete dashboard and analytics representation."""
    kpis: DashboardOverviewKPIs
    pipeline_distribution: List[StatusDistribution]
    work_mode_distribution: List[WorkModeDistribution]
    platform_distribution: List[PlatformSourceDistribution]
    top_in_demand_skills: List[TopInDemandSkill]
    match_score_distribution: List[ScoreBucket]
    recent_activities: List[ActivityItem]


class SkillsGapItem(BaseModel):
    """Detail on a market-demanded skill and candidate coverage."""
    skill_name: str
    category: Optional[str] = "General"
    job_mention_count: int
    is_possessed_by_candidate: bool
    candidate_years_experience: Optional[float] = None


class SkillsGapResponse(BaseModel):
    """Comprehensive skill taxonomy overlap and gap analysis."""
    candidate_total_skills: int
    market_unique_skills: int
    matching_skills_count: int
    missing_skills_count: int
    coverage_percentage: float
    skills_breakdown: List[SkillsGapItem]
