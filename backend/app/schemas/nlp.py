from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    """Supported email categories for classification."""
    JOB = "JOB"
    JOB_ALERT = "JOB_ALERT"
    APPLICATION_UPDATE = "APPLICATION_UPDATE"
    INTERVIEW = "INTERVIEW"
    REJECTION = "REJECTION"
    OFFER = "OFFER"
    PROMOTION = "PROMOTION"
    NEWSLETTER = "NEWSLETTER"
    ADVERTISEMENT = "ADVERTISEMENT"
    OTHER = "OTHER"


class EmailClassificationResult(BaseModel):
    """Result of NLP / LLM email classification."""
    category: EmailCategory
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    reason: str = Field(..., description="Explainable reason why this category was determined")
    signals_detected: List[str] = Field(default_factory=list, description="Key keywords, phrases, or heuristics matched")


class BatchClassifyResponse(BaseModel):
    """Response returned upon batch classifying emails."""
    total_processed: int
    classified_count: int
    failed_count: int
    message: str
