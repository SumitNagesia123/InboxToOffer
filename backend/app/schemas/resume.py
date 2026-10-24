import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResponse(BaseModel):
    """Metadata response returned immediately upon resume upload and text extraction."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    character_count: int
    word_count: int
    page_count: int
    text_preview: str
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    """Full candidate resume entity response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    extracted_text: str
    parsed_summary: Optional[str] = None
    total_experience_years: Optional[float] = None
    education_summary: Optional[Dict[str, Any]] = None
    character_count: int
    word_count: int
    created_at: datetime
    updated_at: datetime


class ContactInfo(BaseModel):
    """Candidate contact and portfolio links."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None


class WorkExperienceItem(BaseModel):
    """Individual work role experience record."""
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    duration_years: Optional[float] = None
    description: Optional[str] = None
    skills_used: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    """Academic background record."""
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None


class SkillItem(BaseModel):
    """Extracted skill item with category and experience."""
    name: str
    category: Optional[str] = "Technical"
    years_experience: Optional[float] = None


class ParsedResumeData(BaseModel):
    """Complete structured breakdown of candidate profile."""
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    total_experience_years: Optional[float] = None
    experience: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    skills: List[SkillItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)


class StructuredResumeResponse(BaseModel):
    """API response containing full structured resume profile and linked skills."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_name: str
    parsed_data: ParsedResumeData
    skills_count: int
    experience_count: int
    education_count: int
    total_experience_years: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ResumeTextResponse(BaseModel):
    """Raw text extraction payload."""
    file_name: str
    character_count: int
    word_count: int
    extracted_text: str


