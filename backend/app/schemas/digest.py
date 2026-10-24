import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UserPreferenceUpdate(BaseModel):
    """Schema for updating candidate job hunt and digest preferences."""
    digest_enabled: Optional[bool] = Field(None, description="Whether to receive daily email digests")
    digest_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$", description="Preferred delivery time in HH:MM format e.g. '22:00'")
    preferred_work_modes: Optional[List[str]] = Field(None, description="Preferred modalities e.g. ['REMOTE', 'HYBRID']")
    min_desired_salary: Optional[float] = Field(None, ge=0.0, description="Minimum compensation threshold")


class UserPreferenceResponse(BaseModel):
    """Public representation of user settings and digest preferences."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    digest_enabled: bool
    digest_time: str
    preferred_work_modes: List[str]
    min_desired_salary: Optional[float]
    created_at: datetime
    updated_at: datetime


class DigestJobItem(BaseModel):
    """Structured job entry highlighted inside the digest."""
    job_id: uuid.UUID
    company_name: str
    title: str
    location: Optional[str] = None
    work_mode: str = "UNKNOWN"
    salary_formatted: Optional[str] = None
    match_score: float
    matched_skills: List[str] = []
    job_url: Optional[str] = None


class DigestPreviewResponse(BaseModel):
    """Full preview of a generated digest for UI display or inspection."""
    recipient_email: str
    subject: str
    date_formatted: str
    total_jobs_evaluated: int
    top_matches_count: int
    top_matches: List[DigestJobItem]
    interview_alerts_count: int
    html_content: str
    text_content: str


class DailyDigestResponse(BaseModel):
    """Record of a dispatched digest."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    sent_at: datetime
    total_emails_processed: int
    new_jobs_count: int
    top_matches_count: int
    recipient_email: str
    status: str


class DailyDigestListResponse(BaseModel):
    """Paginated list of past sent daily digests."""
    items: List[DailyDigestResponse]
    total: int
    skip: int
    limit: int


class TriggerDigestResponse(BaseModel):
    """Response returned upon triggering an on-demand digest execution."""
    success: bool
    message: str
    digest_id: Optional[uuid.UUID] = None
    recipient_email: str
    top_matches_count: int
    delivery_status: str
