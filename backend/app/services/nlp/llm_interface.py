from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.schemas.job import ExtractedJobData
from app.schemas.nlp import EmailClassificationResult
from app.schemas.resume import ParsedResumeData


class LLMProviderInterface(ABC):
    """Abstract interface defining required capabilities for any LLM provider adapter."""

    @abstractmethod
    def classify_email(self, subject: str, sender: str, body: str) -> Optional[EmailClassificationResult]:
        """Classifies email into a specific category with confidence and reasoning."""
        pass

    @abstractmethod
    def extract_job_details(
        self, subject: str, sender: str, body: str, links: Optional[List[str]] = None
    ) -> Optional[ExtractedJobData]:
        """Extracts structured job posting fields from an email."""
        pass

    @abstractmethod
    def parse_resume(self, resume_text: str) -> Optional[ParsedResumeData]:
        """Parses unstructured resume text into a structured profile schema."""
        pass

