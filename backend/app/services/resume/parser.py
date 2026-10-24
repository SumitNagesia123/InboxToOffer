import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.resume import (
    ContactInfo,
    EducationItem,
    ParsedResumeData,
    SkillItem,
    WorkExperienceItem,
)
from app.services.nlp.adapters import get_llm_adapter
from app.services.nlp.extractor import KNOWN_SKILLS


SKILL_CATEGORIES = {
    "Python": "Programming Language",
    "Java": "Programming Language",
    "JavaScript": "Programming Language",
    "TypeScript": "Programming Language",
    "Go": "Programming Language",
    "Golang": "Programming Language",
    "Rust": "Programming Language",
    "C++": "Programming Language",
    "C#": "Programming Language",
    "FastAPI": "Framework",
    "Django": "Framework",
    "Flask": "Framework",
    "React": "Frontend Framework",
    "Next.js": "Frontend Framework",
    "Vue.js": "Frontend Framework",
    "Angular": "Frontend Framework",
    "Spring Boot": "Framework",
    "Node.js": "Runtime / Framework",
    "SQL": "Database",
    "PostgreSQL": "Database",
    "MySQL": "Database",
    "MongoDB": "Database",
    "Redis": "Database",
    "Elasticsearch": "Database / Search",
    "Docker": "DevOps & Containers",
    "Kubernetes": "DevOps & Containers",
    "AWS": "Cloud Infrastructure",
    "GCP": "Cloud Infrastructure",
    "Azure": "Cloud Infrastructure",
    "Terraform": "Infrastructure as Code",
    "CI/CD": "DevOps",
    "Git": "Version Control",
    "REST APIs": "API Architecture",
    "GraphQL": "API Architecture",
    "Kafka": "Messaging / Streaming",
    "Linux": "Operating Systems",
    "Machine Learning": "AI & ML",
    "PyTorch": "AI & ML",
    "TensorFlow": "AI & ML",
    "Pandas": "Data Science",
    "NumPy": "Data Science",
    "Tailwind CSS": "Frontend Styling",
    "Microservices": "Architecture",
    "System Design": "Architecture",
    "Agile": "Methodology",
    "Scrum": "Methodology",
}


DEGREE_PATTERNS = [
    r"(?i)\b(?:bachelor|b\.?s\.?|b\.?a\.?|b\.?tech|b\.?e\.?)\b(?:\s+(?:of|in)\s+([A-Za-z\s]+))?",
    r"(?i)\b(?:master|m\.?s\.?|m\.?a\.?|m\.?tech|m\.?e\.?|m\.?b\.?a\.?)\b(?:\s+(?:of|in)\s+([A-Za-z\s]+))?",
    r"(?i)\b(?:ph\.?d\.?|doctorate)\b(?:\s+(?:of|in)\s+([A-Za-z\s]+))?",
]


class ResumeParser:
    """Hybrid rule-based and AI resume parsing engine."""

    def extract_contact_info(self, text: str) -> ContactInfo:
        """Extracts email, phone, location, LinkedIn, GitHub, and candidate name."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        first_lines = lines[:5] if lines else []

        # 1. Candidate Name (usually top line before headers)
        name: Optional[str] = None
        for line in first_lines:
            clean_line = re.sub(r"^#+\s*", "", line).strip()
            # If not email, phone, or section header
            if (
                clean_line
                and "@" not in clean_line
                and not re.search(r"(?i)\b(resume|curriculum|vitae|summary|experience)\b", clean_line)
                and len(clean_line) <= 40
            ):
                name = clean_line
                break

        # 2. Email Address
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        email = email_match.group(0).lower() if email_match else None

        # 3. Phone Number
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text)
        phone = phone_match.group(0).strip() if phone_match else None

        # 4. Social & Portfolio Links
        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+/?", text, re.IGNORECASE)
        linkedin_url = linkedin_match.group(0) if linkedin_match else None
        if linkedin_url and not linkedin_url.startswith("http"):
            linkedin_url = f"https://{linkedin_url}"

        github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+/?", text, re.IGNORECASE)
        github_url = github_match.group(0) if github_match else None
        if github_url and not github_url.startswith("http"):
            github_url = f"https://{github_url}"

        # 5. Location
        location: Optional[str] = None
        loc_match = re.search(r"(?i)(?:location|address|based in)[:\s]*([A-Za-z\s,.-]{3,40})", text)
        if loc_match:
            location = loc_match.group(1).strip()
        else:
            # Check city/state patterns in header
            for line in first_lines:
                city_match = re.search(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?),\s*([A-Z]{2}|[A-Z][a-zA-Z]+)\b", line)
                if city_match:
                    location = city_match.group(0).strip()
                    break

        return ContactInfo(
            name=name,
            email=email,
            phone=phone,
            location=location,
            linkedin_url=linkedin_url,
            github_url=github_url,
            portfolio_url=None,
        )

    def extract_sections(self, text: str) -> Dict[str, str]:
        """Segments resume text into distinct structural blocks based on common section headers."""
        headers = [
            "SUMMARY", "OBJECTIVE", "PROFESSIONAL SUMMARY",
            "EXPERIENCE", "WORK EXPERIENCE", "EMPLOYMENT HISTORY", "WORK HISTORY",
            "EDUCATION", "ACADEMIC BACKGROUND",
            "SKILLS", "TECHNICAL SKILLS", "AREAS OF EXPERTISE",
            "PROJECTS", "PERSONAL PROJECTS",
            "CERTIFICATIONS", "LICENSES",
        ]

        pattern = r"(?i)(?:^|\n)(#{1,3}\s*)?(" + "|".join(re.escape(h) for h in headers) + r")[:\s]*\n"
        splits = list(re.finditer(pattern, text))

        sections: Dict[str, str] = {}
        if not splits:
            sections["BODY"] = text
            return sections

        # Header prefix before first section
        if splits[0].start() > 0:
            sections["HEADER"] = text[:splits[0].start()].strip()

        for i, match in enumerate(splits):
            raw_title = match.group(2).upper()
            canonical_key = "SUMMARY"
            if "EXPERIENCE" in raw_title or "EMPLOYMENT" in raw_title or "WORK" in raw_title:
                canonical_key = "EXPERIENCE"
            elif "EDUCATION" in raw_title or "ACADEMIC" in raw_title:
                canonical_key = "EDUCATION"
            elif "SKILL" in raw_title or "EXPERTISE" in raw_title:
                canonical_key = "SKILLS"
            elif "PROJECT" in raw_title:
                canonical_key = "PROJECTS"
            elif "CERTIF" in raw_title:
                canonical_key = "CERTIFICATIONS"

            start_idx = match.end()
            end_idx = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            sections[canonical_key] = text[start_idx:end_idx].strip()

        return sections

    def extract_work_experience(self, exp_text: str) -> Tuple[List[WorkExperienceItem], Optional[float]]:
        """Parses experience items and estimates total experience years."""
        if not exp_text:
            return [], None

        items: List[WorkExperienceItem] = []
        # Match date ranges like "Jan 2020 - Present", "2018 - 2021", "06/2019 - Current"
        date_pattern = r"(?i)\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-1]?\d)[a-z]*\s+)?(\d{4})\s*(?:-|–|to)\s*((?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|[0-1]?\d)[a-z]*\s+)?\d{4}|Present|Current|Now)\b"

        # Split experience by blocks or lines
        blocks = re.split(r"\n{2,}", exp_text)
        total_years = 0.0

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            date_match = re.search(date_pattern, block)
            start_year = None
            end_year = None
            is_current = False
            duration = None

            if date_match:
                start_year = int(date_match.group(2))
                end_str = date_match.group(3).lower()
                if end_str in ("present", "current", "now"):
                    is_current = True
                    end_year = datetime.now().year
                else:
                    year_only = re.search(r"\d{4}", end_str)
                    end_year = int(year_only.group(0)) if year_only else datetime.now().year

                if start_year and end_year and end_year >= start_year:
                    duration = float(end_year - start_year) or 1.0
                    total_years += duration

            # Attempt to extract role and company
            first_line = lines[0]
            clean_first = re.sub(date_pattern, "", first_line).strip()
            parts = re.split(r"(?i)\s+(?:at|@|,|-|–|\|)\s+", clean_first)

            role = parts[0].strip() if parts else "Software Engineer"
            company = parts[1].strip() if len(parts) > 1 else "Technology Company"

            # Clean role and company strings
            role = re.sub(r"^[^\w]+|[^\w]+$", "", role)
            company = re.sub(r"^[^\w]+|[^\w]+$", "", company)

            # Match skills mentioned in this block
            used_skills = [s for s in KNOWN_SKILLS if re.search(rf"\b{re.escape(s)}\b", block, re.IGNORECASE)]

            items.append(
                WorkExperienceItem(
                    company=company or "Company",
                    role=role or "Role",
                    start_date=str(start_year) if start_year else None,
                    end_date="Present" if is_current else (str(end_year) if end_year else None),
                    is_current=is_current,
                    duration_years=duration,
                    description="\n".join(lines[1:]) if len(lines) > 1 else block,
                    skills_used=used_skills,
                )
            )

        exp_years = round(total_years, 1) if total_years > 0 else None
        return items, exp_years

    def extract_education(self, edu_text: str) -> List[EducationItem]:
        """Extracts degrees, institutions, and graduation years."""
        if not edu_text:
            return []

        items: List[EducationItem] = []
        blocks = re.split(r"\n{2,}", edu_text)

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            year_match = re.search(r"\b(19\d{2}|20\d{2})\b", block)
            grad_year = int(year_match.group(1)) if year_match else None

            gpa_match = re.search(r"(?i)\bGPA[:\s]*([0-4]\.\d{1,2}(?:/[0-4]\.0)?)\b", block)
            gpa = gpa_match.group(1) if gpa_match else None

            degree = None
            field = None
            for pat in DEGREE_PATTERNS:
                deg_match = re.search(pat, block)
                if deg_match:
                    degree = deg_match.group(0).strip()
                    if deg_match.groups() and deg_match.group(1):
                        field = deg_match.group(1).strip()
                    break

            institution = lines[0]
            if degree and degree in institution:
                # If first line was the degree, second line is institution
                if len(lines) > 1:
                    institution = lines[1]
                else:
                    institution = "University"

            # Clean institution line of date/gpa noise
            institution = re.sub(r"\b(19\d{2}|20\d{2})\b", "", institution).strip(" ,-|–")

            items.append(
                EducationItem(
                    institution=institution or "University",
                    degree=degree,
                    field_of_study=field,
                    graduation_year=grad_year,
                    gpa=gpa,
                )
            )

        return items

    def extract_skills(self, text: str) -> List[SkillItem]:
        """Scans complete resume against recognized skill catalog."""
        skill_items: List[SkillItem] = []
        for skill in KNOWN_SKILLS:
            pattern = rf"\b{re.escape(skill)}\b"
            if re.search(pattern, text, re.IGNORECASE):
                cat = SKILL_CATEGORIES.get(skill, "Technical")
                skill_items.append(
                    SkillItem(
                        name=skill,
                        category=cat,
                    )
                )
        return skill_items

    def parse(self, resume_text: str) -> ParsedResumeData:
        """Executes full resume parsing using LLM adapter with robust rule-based fallback."""
        # 1. Attempt LLM parsing if configured
        llm_adapter = get_llm_adapter()
        if llm_adapter:
            try:
                llm_result = llm_adapter.parse_resume(resume_text)
                if llm_result and (llm_result.experience or llm_result.skills or llm_result.education):
                    return llm_result
            except Exception as e:
                logger.warning("LLM resume parsing failed, falling back to heuristic parser: %s", str(e))

        # 2. Heuristic parsing pipeline
        sections = self.extract_sections(resume_text)
        contact = self.extract_contact_info(resume_text)

        summary = sections.get("SUMMARY")
        if not summary and "HEADER" in sections:
            summary = sections["HEADER"]

        experience_items, exp_years = self.extract_work_experience(sections.get("EXPERIENCE", ""))
        education_items = self.extract_education(sections.get("EDUCATION", ""))
        skills = self.extract_skills(resume_text)

        # Certifications
        cert_section = sections.get("CERTIFICATIONS", "")
        certs = [c.strip("-* \t") for c in cert_section.split("\n") if c.strip("-* \t")] if cert_section else []

        return ParsedResumeData(
            contact_info=contact,
            summary=summary[:500] if summary else None,
            total_experience_years=exp_years,
            experience=experience_items,
            education=education_items,
            skills=skills,
            certifications=certs,
            projects=[],
        )


resume_parser = ResumeParser()
