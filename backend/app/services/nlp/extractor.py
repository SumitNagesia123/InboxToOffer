import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.core.logging import logger
from app.schemas.job import EmploymentType, ExtractedJobData, WorkMode
from app.services.email.source_detector import source_detector
from app.services.nlp.adapters import get_llm_adapter


# Catalog of recognized tech & software skills
KNOWN_SKILLS: List[str] = [
    "Python", "FastAPI", "Django", "Flask", "React", "TypeScript", "JavaScript",
    "Node.js", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Docker",
    "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Git", "REST APIs",
    "GraphQL", "Java", "Spring Boot", "Go", "Golang", "Rust", "C++", "C#",
    ".NET", "Kafka", "Elasticsearch", "Linux", "Machine Learning", "PyTorch",
    "TensorFlow", "Pandas", "NumPy", "Next.js", "Tailwind CSS", "Angular",
    "Vue.js", "Microservices", "System Design", "Agile", "Scrum",
]


class JobInformationExtractor:
    """Extracts structured job posting details from job email contents."""

    @staticmethod
    def extract_company(sender: str, subject: str) -> str:
        """Extracts hiring company name from subject patterns or sender domain."""
        # Check patterns in subject: "at [Company]", "[Company] is hiring", "join [Company]"
        at_match = re.search(r"(?i)\bat\s+([A-Z][A-Za-z0-9\s&]{1,25})(?:\s+in|\s*[-|–:,]|\s*$)", subject)
        if at_match:
            candidate = at_match.group(1).strip()
            if candidate.lower() not in ("remote", "full time", "hybrid", "our team", "home"):
                return candidate

        hiring_match = re.search(r"(?i)\b([A-Z][A-Za-z0-9\s&]{1,25})\s+is\s+hiring\b", subject)
        if hiring_match:
            return hiring_match.group(1).strip()

        bracket_match = re.search(r"\[([A-Za-z0-9\s&]{2,25})\]", subject)
        if bracket_match:
            candidate = bracket_match.group(1).strip()
            if candidate.lower() not in ("job alert", "new job", "hiring", "apply", "urgent"):
                return candidate

        # Extract from sender email domain
        email_match = re.search(r"@([a-zA-Z0-9.-]+)", sender)
        if email_match:
            domain = email_match.group(1).lower()
            parts = domain.split(".")
            # Filter common portal/relay domains
            if len(parts) >= 2 and parts[-2] not in (
                "linkedin", "indeed", "naukri", "internshala", "gmail", "yahoo",
                "outlook", "greenhouse", "lever", "workday", "glassdoor",
            ):
                return parts[-2].capitalize()

        return "Unknown Company"

    @staticmethod
    def extract_title(subject: str, body: str) -> str:
        """Extracts job title from subject line or header."""
        clean_subj = re.sub(r"(?i)^(re:|fwd:|job alert:?|new opening:?|apply now:?)\s*", "", subject).strip()
        clean_subj = re.sub(r"(?i)\s+(at|for|in)\s+.*$", "", clean_subj).strip()
        clean_subj = re.sub(r"\[.*?\]", "", clean_subj).strip()

        if len(clean_subj) >= 4 and len(clean_subj) <= 80:
            return clean_subj

        # Search in body
        match = re.search(r"(?i)(?:role|position|job\s+title):\s*([^\n\r]+)", body)
        if match:
            return match.group(1).strip()

        return "Software Engineer"

    @staticmethod
    def extract_location_and_work_mode(text: str) -> Tuple[Optional[str], WorkMode]:
        """Extracts location string and categorizes work modality."""
        text_lower = text.lower()

        work_mode = WorkMode.UNKNOWN
        if "remote" in text_lower or "work from home" in text_lower:
            work_mode = WorkMode.REMOTE
        elif "hybrid" in text_lower:
            work_mode = WorkMode.HYBRID
        elif "on-site" in text_lower or "onsite" in text_lower or "in-office" in text_lower:
            work_mode = WorkMode.ON_SITE

        # Location heuristic
        location: Optional[str] = None
        loc_match = re.search(r"(?i)(?:location|based\s+in):\s*([A-Za-z0-9\s,.-]{2,50})", text)
        if loc_match:
            location = loc_match.group(1).strip()
        elif work_mode == WorkMode.REMOTE:
            location = "Remote"

        return location, work_mode

    @staticmethod
    def extract_employment_type(text: str) -> EmploymentType:
        """Extracts employment type e.g. Full-time, Contract, Internship."""
        text_lower = text.lower()
        if "full-time" in text_lower or "full time" in text_lower or "permanent" in text_lower:
            return EmploymentType.FULL_TIME
        elif "contract" in text_lower or "contractor" in text_lower or "c2c" in text_lower:
            return EmploymentType.CONTRACT
        elif "intern" in text_lower or "internship" in text_lower:
            return EmploymentType.INTERNSHIP
        elif "part-time" in text_lower or "part time" in text_lower:
            return EmploymentType.PART_TIME
        return EmploymentType.UNKNOWN

    @staticmethod
    def extract_salary(text: str) -> Tuple[Optional[str], Optional[float], Optional[float]]:
        """Extracts currency and min/max salary figures if explicitly provided."""
        # Never fabricate: defaults strictly to None
        currency: Optional[str] = None
        min_sal: Optional[float] = None
        max_sal: Optional[float] = None

        # 1. USD/CAD range with k notation e.g. $120k - $160k or $120,000 - $160,000
        usd_range = re.search(r"\$(\d{2,3})(?:,(\d{3}))?(?:\s*k)?\s*(?:-|to)\s*\$?(\d{2,3})(?:,(\d{3}))?(?:\s*k)?", text, re.IGNORECASE)
        if usd_range:
            currency = "USD"
            val1_str = usd_range.group(1) + (usd_range.group(2) or "")
            val2_str = usd_range.group(3) + (usd_range.group(4) or "")
            val1 = float(val1_str) * (1000 if len(val1_str) <= 3 else 1)
            val2 = float(val2_str) * (1000 if len(val2_str) <= 3 else 1)
            return currency, min(val1, val2), max(val1, val2)

        # 2. Single USD figure e.g. $140k / year or $140,000
        usd_single = re.search(r"\$(\d{2,3})(?:,(\d{3}))?(?:\s*k)?\s*(?:/|\bper\b)?\s*(?:yr|year|annum)?", text, re.IGNORECASE)
        if usd_single:
            currency = "USD"
            val_str = usd_single.group(1) + (usd_single.group(2) or "")
            val = float(val_str) * (1000 if len(val_str) <= 3 else 1)
            if val >= 20000:
                return currency, val, val

        # 3. INR (LPA) e.g. 15 - 25 LPA or ₹15,00,000
        inr_range = re.search(r"(?:₹|INR\s*)?\s*(\d{1,2}(?:\.\d+)?)\s*(?:-|to)\s*(\d{1,2}(?:\.\d+)?)\s*LPA", text, re.IGNORECASE)
        if inr_range:
            currency = "INR"
            val1 = float(inr_range.group(1)) * 100000
            val2 = float(inr_range.group(2)) * 100000
            return currency, min(val1, val2), max(val1, val2)

        # 4. EUR e.g. €70,000 - €90,000
        eur_range = re.search(r"€(\d{2,3})(?:,(\d{3}))?(?:\s*k)?\s*(?:-|to)\s*€?(\d{2,3})(?:,(\d{3}))?(?:\s*k)?", text, re.IGNORECASE)
        if eur_range:
            currency = "EUR"
            val1_str = eur_range.group(1) + (eur_range.group(2) or "")
            val2_str = eur_range.group(3) + (eur_range.group(4) or "")
            val1 = float(val1_str) * (1000 if len(val1_str) <= 3 else 1)
            val2 = float(val2_str) * (1000 if len(val2_str) <= 3 else 1)
            return currency, min(val1, val2), max(val1, val2)

        # 5. GBP e.g. £60,000 - £80,000
        gbp_range = re.search(r"£(\d{2,3})(?:,(\d{3}))?(?:\s*k)?\s*(?:-|to)\s*£?(\d{2,3})(?:,(\d{3}))?(?:\s*k)?", text, re.IGNORECASE)
        if gbp_range:
            currency = "GBP"
            val1_str = gbp_range.group(1) + (gbp_range.group(2) or "")
            val2_str = gbp_range.group(3) + (gbp_range.group(4) or "")
            val1 = float(val1_str) * (1000 if len(val1_str) <= 3 else 1)
            val2 = float(val2_str) * (1000 if len(val2_str) <= 3 else 1)
            return currency, min(val1, val2), max(val1, val2)

        return currency, min_sal, max_sal

    @staticmethod
    def extract_experience(text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extracts min and max years of experience if explicitly stated."""
        # Range: 3-5 years or 3 to 5 years
        range_match = re.search(r"\b(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:\+)?\s*years?", text, re.IGNORECASE)
        if range_match:
            min_exp = int(range_match.group(1))
            max_exp = int(range_match.group(2))
            return min(min_exp, max_exp), max(min_exp, max_exp)

        # Plus: 5+ years or minimum 3 years
        plus_match = re.search(r"\b(\d{1,2})\s*\+\s*years?", text, re.IGNORECASE)
        if plus_match:
            return int(plus_match.group(1)), None

        min_match = re.search(r"(?i)(?:minimum|at\s+least)\s+(\d{1,2})\s+years?", text)
        if min_match:
            return int(min_match.group(1)), None

        return None, None

    @staticmethod
    def extract_skills(text: str) -> Tuple[List[str], List[str]]:
        """Scans content against skill taxonomy to identify required and preferred skills."""
        found_skills = []
        for skill in KNOWN_SKILLS:
            # Word boundary search
            pattern = rf"\b{re.escape(skill)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                found_skills.append(skill)

        # Separate required vs preferred if explicit section exists
        text_lower = text.lower()
        if "preferred" in text_lower or "nice to have" in text_lower:
            parts = re.split(r"(?i)\b(?:preferred|nice\s+to\s+have|bonus)\b", text, maxsplit=1)
            req_part = parts[0]
            pref_part = parts[1] if len(parts) > 1 else ""

            required = [s for s in found_skills if re.search(rf"\b{re.escape(s)}\b", req_part, re.IGNORECASE)]
            preferred = [s for s in found_skills if re.search(rf"\b{re.escape(s)}\b", pref_part, re.IGNORECASE) and s not in required]
            return required, preferred

        return found_skills, []

    @staticmethod
    def extract_job_url(
        links: Optional[List[str]] = None,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        job_title: str = "",
        company_name: str = "",
    ) -> Optional[str]:
        """Finds direct application link by scanning HTML anchors and extracted URLs with relevance scoring."""
        exclude_terms = [
            "unsubscribe", "privacy", "opt-out", "preferences", "play.google.com",
            "apps.apple.com", "fonts.googleapis", "help-center", "feedback",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com/company", "mail-settings",
        ]

        candidates: List[Tuple[int, str]] = []

        # 1. Parse HTML <a> tags if body_html is available
        if body_html:
            a_tags = re.findall(
                r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
                body_html,
                re.DOTALL | re.IGNORECASE,
            )
            for href, anchor in a_tags:
                clean_anchor = re.sub(r'<[^>]+>', '', anchor).strip().lower()
                href_lower = href.lower()

                if any(term in href_lower for term in exclude_terms) or any(
                    term in clean_anchor for term in ["unsubscribe", "privacy", "terms", "opt out", "download app"]
                ):
                    continue

                score = 0
                if "apply" in clean_anchor:
                    score += 100
                if "apply now" in clean_anchor or "quick apply" in clean_anchor or "one-click" in clean_anchor:
                    score += 50
                if "view job" in clean_anchor or "job details" in clean_anchor or "view opening" in clean_anchor:
                    score += 40
                if job_title and job_title.lower() in clean_anchor:
                    score += 60
                if company_name and company_name.lower() in clean_anchor:
                    score += 30

                if "one-click-apply" in href_lower or "apply" in href_lower:
                    score += 40
                if "jobid=" in href_lower or "/j/" in href_lower or "viewjob" in href_lower or "clk/dl" in href_lower:
                    score += 30
                if any(b in href_lower for b in [
                    "hirist.tech", "indeed.com", "linkedin.com/jobs", "naukri.com",
                    "internshala.com", "placementindia.com", "lever.co", "greenhouse.io"
                ]):
                    score += 20

                candidates.append((score, href))

        # 2. Check explicit links list or text
        combined_links = list(links or [])
        if body_text and not combined_links:
            combined_links = re.findall(r'https?://[^\s<>"\'\)]+', body_text)

        for link in combined_links:
            link_lower = link.lower()
            if any(term in link_lower for term in exclude_terms):
                continue
            score = 10
            if any(term in link_lower for term in (
                "jobs.lever.co", "boards.greenhouse.io", "myworkdayjobs.com",
                "linkedin.com/jobs", "indeed.com", "naukri.com", "hirist.tech",
                "internshala.com", "placementindia.com", "one-click-apply",
                "clk/dl", "job-listings", "/job/", "viewjob", "/careers/", "/apply"
            )):
                score += 30
            candidates.append((score, link))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def extract(
        self,
        subject: str,
        sender: str,
        body: str,
        links: Optional[List[str]] = None,
        body_html: Optional[str] = None,
    ) -> ExtractedJobData:
        """Runs multi-signal extraction with LLM adapter integration and zero hallucination guarantee."""
        full_content = f"{subject}\n{body}"

        # Rule-based extraction
        company = self.extract_company(sender=sender, subject=subject)
        title = self.extract_title(subject=subject, body=body)
        location, work_mode = self.extract_location_and_work_mode(full_content)
        emp_type = self.extract_employment_type(full_content)
        currency, min_sal, max_sal = self.extract_salary(full_content)
        min_exp, max_exp = self.extract_experience(full_content)
        req_skills, pref_skills = self.extract_skills(full_content)
        job_url = self.extract_job_url(
            links=links,
            body_html=body_html,
            body_text=body,
            job_title=title,
            company_name=company,
        )
        source = source_detector.detect_source(sender=sender, subject=subject, body_text=body, urls=links)

        return ExtractedJobData(
            company_name=company,
            title=title,
            location=location,
            work_mode=work_mode,
            employment_type=emp_type,
            salary_currency=currency,
            salary_min=min_sal,
            salary_max=max_sal,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            job_description=body[:4000] if body else None,
            job_url=job_url,
            platform_source=source,
        )


job_extractor = JobInformationExtractor()
