import json
import re
from typing import Any, Dict, List, Optional
import requests

from app.core.config import settings
from app.core.logging import logger
from app.schemas.job import EmploymentType, ExtractedJobData, WorkMode
from app.schemas.nlp import EmailCategory, EmailClassificationResult
from app.schemas.resume import ContactInfo, EducationItem, ParsedResumeData, SkillItem, WorkExperienceItem
from app.services.nlp.llm_interface import LLMProviderInterface


CLASSIFICATION_PROMPT_TEMPLATE = """You are an expert email classifier for a career and job application assistant.
Classify the following email into exactly ONE of the following categories:
- JOB (A specific job posting, requisition, or recruiter message offering a specific open role)
- JOB_ALERT (A digest or automated alert containing multiple job recommendations from LinkedIn, Indeed, Naukri, etc.)
- APPLICATION_UPDATE (Acknowledgement that an application was received or is in review)
- INTERVIEW (Invitation to an interview, screening call, technical assessment, or scheduling link)
- REJECTION (Notice that the candidate is not selected or the position was filled)
- OFFER (Official job offer or letter of intent)
- PROMOTION (Marketing for career coaching, resume services, paid bootcamps, or events)
- NEWSLETTER (Industry news, blog digest, or weekly editorial)
- ADVERTISEMENT (Unrelated commercial products or spam)
- OTHER (Personal email, receipt, or unrelated correspondence)

Email Sender: {sender}
Email Subject: {subject}
Email Body:
{body}

Respond with ONLY valid JSON adhering strictly to this schema:
{{
  "category": "JOB" | "JOB_ALERT" | "APPLICATION_UPDATE" | "INTERVIEW" | "REJECTION" | "OFFER" | "PROMOTION" | "NEWSLETTER" | "ADVERTISEMENT" | "OTHER",
  "confidence": 0.0 to 1.0,
  "reason": "Brief explanation of why this category was chosen",
  "signals_detected": ["list", "of", "detected", "keywords", "or", "phrases"]
}}
"""

JOB_EXTRACTION_PROMPT_TEMPLATE = """You are an expert job information extraction system.
Extract structured details from the following job email.
IMPORTANT: Do NOT hallucinate or guess. If a field (such as salary, experience, or url) is not explicitly mentioned, return null.

Email Sender: {sender}
Email Subject: {subject}
Email Links: {links}
Email Body:
{body}

Respond with ONLY valid JSON adhering strictly to this schema:
{{
  "company_name": "string",
  "title": "string",
  "location": "string or null",
  "work_mode": "REMOTE" | "HYBRID" | "ON_SITE" | "UNKNOWN",
  "employment_type": "FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERNSHIP" | "UNKNOWN",
  "salary_currency": "USD" | "INR" | "EUR" | "GBP" | null,
  "salary_min": float or null,
  "salary_max": float or null,
  "min_experience_years": int or null,
  "max_experience_years": int or null,
  "required_skills": ["list", "of", "strings"],
  "preferred_skills": ["list", "of", "strings"],
  "job_url": "string or null"
}}
"""

RESUME_PARSING_PROMPT_TEMPLATE = """You are an expert resume parsing engine.
Extract structured profile details from the following candidate resume text.
Do NOT hallucinate or fabricate facts; if a field is not present in the text, return null or an empty list.

Resume Text:
{resume_text}

Respond with ONLY valid JSON adhering strictly to this schema:
{{
  "contact_info": {{
    "name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "location": "string or null",
    "linkedin_url": "string or null",
    "github_url": "string or null",
    "portfolio_url": "string or null"
  }},
  "summary": "string or null",
  "total_experience_years": float or null,
  "experience": [
    {{
      "company": "string",
      "role": "string",
      "start_date": "string or null",
      "end_date": "string or null",
      "is_current": boolean,
      "duration_years": float or null,
      "description": "string or null",
      "skills_used": ["string"]
    }}
  ],
  "education": [
    {{
      "institution": "string",
      "degree": "string or null",
      "field_of_study": "string or null",
      "graduation_year": int or null,
      "gpa": "string or null"
    }}
  ],
  "skills": [
    {{
      "name": "string",
      "category": "Technical",
      "years_experience": float or null
    }}
  ],
  "certifications": ["string"],
  "projects": []
}}
"""


def _parse_llm_json(response_text: str) -> Optional[Dict[str, Any]]:
    """Extracts and parses JSON object from LLM response text."""
    if not response_text:
        return None
    try:
        # Check for markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Check raw JSON
        raw_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
        if raw_match:
            return json.loads(raw_match.group(1))

        return json.loads(response_text)
    except Exception as e:
        logger.warning("Could not parse JSON from LLM response: %s", str(e))
        return None


def _parse_job_data(parsed: Dict[str, Any], default_source: str = "OTHER") -> Optional[ExtractedJobData]:
    """Helper to convert parsed LLM dictionary into validated ExtractedJobData."""
    try:
        raw_work_mode = str(parsed.get("work_mode", "UNKNOWN")).upper()
        work_mode = WorkMode[raw_work_mode] if raw_work_mode in WorkMode.__members__ else WorkMode.UNKNOWN

        raw_emp_type = str(parsed.get("employment_type", "UNKNOWN")).upper()
        emp_type = EmploymentType[raw_emp_type] if raw_emp_type in EmploymentType.__members__ else EmploymentType.UNKNOWN

        return ExtractedJobData(
            company_name=parsed.get("company_name", "Unknown Company"),
            title=parsed.get("title", "Unknown Role"),
            location=parsed.get("location"),
            work_mode=work_mode,
            employment_type=emp_type,
            salary_currency=parsed.get("salary_currency"),
            salary_min=float(parsed["salary_min"]) if parsed.get("salary_min") is not None else None,
            salary_max=float(parsed["salary_max"]) if parsed.get("salary_max") is not None else None,
            min_experience_years=int(parsed["min_experience_years"]) if parsed.get("min_experience_years") is not None else None,
            max_experience_years=int(parsed["max_experience_years"]) if parsed.get("max_experience_years") is not None else None,
            required_skills=parsed.get("required_skills") or [],
            preferred_skills=parsed.get("preferred_skills") or [],
            job_url=parsed.get("job_url"),
            platform_source=parsed.get("platform_source", default_source),
        )
    except Exception as e:
        logger.warning("Could not convert parsed JSON to ExtractedJobData: %s", str(e))
        return None


def _parse_resume_data(parsed: Dict[str, Any]) -> Optional[ParsedResumeData]:
    """Helper to convert parsed LLM dictionary into validated ParsedResumeData."""
    try:
        contact_dict = parsed.get("contact_info") or {}
        contact = ContactInfo(
            name=contact_dict.get("name"),
            email=contact_dict.get("email"),
            phone=contact_dict.get("phone"),
            location=contact_dict.get("location"),
            linkedin_url=contact_dict.get("linkedin_url"),
            github_url=contact_dict.get("github_url"),
            portfolio_url=contact_dict.get("portfolio_url"),
        )

        experiences = []
        for exp in parsed.get("experience") or []:
            if isinstance(exp, dict) and exp.get("company") and exp.get("role"):
                experiences.append(
                    WorkExperienceItem(
                        company=str(exp["company"]),
                        role=str(exp["role"]),
                        start_date=exp.get("start_date"),
                        end_date=exp.get("end_date"),
                        is_current=bool(exp.get("is_current", False)),
                        duration_years=float(exp["duration_years"]) if exp.get("duration_years") is not None else None,
                        description=exp.get("description"),
                        skills_used=exp.get("skills_used") or [],
                    )
                )

        educations = []
        for edu in parsed.get("education") or []:
            if isinstance(edu, dict) and edu.get("institution"):
                educations.append(
                    EducationItem(
                        institution=str(edu["institution"]),
                        degree=edu.get("degree"),
                        field_of_study=edu.get("field_of_study"),
                        graduation_year=int(edu["graduation_year"]) if edu.get("graduation_year") is not None else None,
                        gpa=str(edu["gpa"]) if edu.get("gpa") is not None else None,
                    )
                )

        skills = []
        for sk in parsed.get("skills") or []:
            if isinstance(sk, dict) and sk.get("name"):
                skills.append(
                    SkillItem(
                        name=str(sk["name"]),
                        category=sk.get("category", "Technical"),
                        years_experience=float(sk["years_experience"]) if sk.get("years_experience") is not None else None,
                    )
                )
            elif isinstance(sk, str) and sk.strip():
                skills.append(SkillItem(name=sk.strip()))

        return ParsedResumeData(
            contact_info=contact,
            summary=parsed.get("summary"),
            total_experience_years=float(parsed["total_experience_years"]) if parsed.get("total_experience_years") is not None else None,
            experience=experiences,
            education=educations,
            skills=skills,
            certifications=parsed.get("certifications") or [],
            projects=parsed.get("projects") or [],
        )
    except Exception as e:
        logger.warning("Could not convert parsed JSON to ParsedResumeData: %s", str(e))
        return None


class GeminiAdapter(LLMProviderInterface):
    """Google Gemini LLM provider adapter."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    def classify_email(self, subject: str, sender: str, body: str) -> Optional[EmailClassificationResult]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            body=body[:3000],
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _parse_llm_json(text)
                if parsed and "category" in parsed:
                    return EmailClassificationResult(
                        category=EmailCategory(parsed["category"]),
                        confidence=float(parsed.get("confidence", 0.9)),
                        reason=parsed.get("reason", "Classified by Gemini"),
                        signals_detected=parsed.get("signals_detected", []),
                    )
        except Exception as e:
            logger.warning("Gemini classification request failed: %s", str(e))
        return None

    def extract_job_details(
        self, subject: str, sender: str, body: str, links: Optional[List[str]] = None
    ) -> Optional[ExtractedJobData]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = JOB_EXTRACTION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            links=", ".join(links) if links else "None",
            body=body[:3000],
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _parse_llm_json(text)
                if parsed and "title" in parsed and "company_name" in parsed:
                    return _parse_job_data(parsed)
        except Exception as e:
            logger.warning("Gemini job extraction request failed: %s", str(e))
        return None

    def parse_resume(self, resume_text: str) -> Optional[ParsedResumeData]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = RESUME_PARSING_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
        }

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = _parse_llm_json(text)
                if parsed:
                    return _parse_resume_data(parsed)
        except Exception as e:
            logger.warning("Gemini resume parsing request failed: %s", str(e))
        return None


class OllamaAdapter(LLMProviderInterface):
    """Local Ollama LLM provider adapter."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3:latest"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def classify_email(self, subject: str, sender: str, body: str) -> Optional[EmailClassificationResult]:
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            body=body[:3000],
        )

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
                timeout=15,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                parsed = _parse_llm_json(text)
                if parsed and "category" in parsed:
                    return EmailClassificationResult(
                        category=EmailCategory(parsed["category"]),
                        confidence=float(parsed.get("confidence", 0.85)),
                        reason=parsed.get("reason", "Classified by Ollama"),
                        signals_detected=parsed.get("signals_detected", []),
                    )
        except Exception as e:
            logger.warning("Ollama classification request failed: %s", str(e))
        return None

    def extract_job_details(
        self, subject: str, sender: str, body: str, links: Optional[List[str]] = None
    ) -> Optional[ExtractedJobData]:
        prompt = JOB_EXTRACTION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            links=", ".join(links) if links else "None",
            body=body[:3000],
        )

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
                timeout=15,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                parsed = _parse_llm_json(text)
                if parsed and "title" in parsed and "company_name" in parsed:
                    return _parse_job_data(parsed)
        except Exception as e:
            logger.warning("Ollama job extraction request failed: %s", str(e))
        return None

    def parse_resume(self, resume_text: str) -> Optional[ParsedResumeData]:
        prompt = RESUME_PARSING_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
                timeout=20,
            )
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                parsed = _parse_llm_json(text)
                if parsed:
                    return _parse_resume_data(parsed)
        except Exception as e:
            logger.warning("Ollama resume parsing request failed: %s", str(e))
        return None


class OpenAIAdapter(LLMProviderInterface):
    """OpenAI API provider adapter."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def classify_email(self, subject: str, sender: str, body: str) -> Optional[EmailClassificationResult]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            body=body[:3000],
        )

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise JSON career email classifier."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = _parse_llm_json(content)
                if parsed and "category" in parsed:
                    return EmailClassificationResult(
                        category=EmailCategory(parsed["category"]),
                        confidence=float(parsed.get("confidence", 0.95)),
                        reason=parsed.get("reason", "Classified by OpenAI"),
                        signals_detected=parsed.get("signals_detected", []),
                    )
        except Exception as e:
            logger.warning("OpenAI classification request failed: %s", str(e))
        return None

    def extract_job_details(
        self, subject: str, sender: str, body: str, links: Optional[List[str]] = None
    ) -> Optional[ExtractedJobData]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = JOB_EXTRACTION_PROMPT_TEMPLATE.format(
            sender=sender,
            subject=subject,
            links=", ".join(links) if links else "None",
            body=body[:3000],
        )

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise JSON job detail extractor. Return null for missing fields."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = _parse_llm_json(content)
                if parsed and "title" in parsed and "company_name" in parsed:
                    return _parse_job_data(parsed)
        except Exception as e:
            logger.warning("OpenAI job extraction request failed: %s", str(e))
        return None

    def parse_resume(self, resume_text: str) -> Optional[ParsedResumeData]:
        if not self.api_key or self.api_key.startswith("mock_"):
            return None

        prompt = RESUME_PARSING_PROMPT_TEMPLATE.format(resume_text=resume_text[:4000])
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise JSON resume parsing system."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                parsed = _parse_llm_json(content)
                if parsed:
                    return _parse_resume_data(parsed)
        except Exception as e:
            logger.warning("OpenAI resume parsing request failed: %s", str(e))
        return None


def get_llm_adapter() -> Optional[LLMProviderInterface]:
    """Factory creating the appropriate LLM adapter based on application configuration."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        return GeminiAdapter(api_key=settings.LLM_API_KEY)
    elif provider == "ollama":
        return OllamaAdapter(base_url=settings.OLLAMA_BASE_URL)
    elif provider in ("openai", "chatgpt"):
        return OpenAIAdapter(api_key=settings.LLM_API_KEY)
    return None
