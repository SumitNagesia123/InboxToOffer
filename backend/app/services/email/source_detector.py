import re
from typing import Dict, List, Optional
from urllib.parse import urlparse


class PlatformSourceDetector:
    """Detects job origin platform or source from sender email, subject, and body URLs."""

    # Platform definitions: patterns to match against sender, subject, or links
    PLATFORM_PATTERNS: Dict[str, Dict[str, List[str]]] = {
        "LinkedIn": {
            "senders": ["linkedin.com", "linkedinmail.com"],
            "domains": ["linkedin.com", "lnkd.in"],
            "keywords": ["linkedin job", "linkedin alert"],
        },
        "Indeed": {
            "senders": ["indeed.com", "indeedmail.com", "indeedemail.com"],
            "domains": ["indeed.com"],
            "keywords": ["indeed job", "indeed alert"],
        },
        "Naukri": {
            "senders": ["naukri.com", "naukrialerts.com"],
            "domains": ["naukri.com"],
            "keywords": ["naukri.com", "naukri fastforward"],
        },
        "Internshala": {
            "senders": ["internshala.com"],
            "domains": ["internshala.com"],
            "keywords": ["internshala"],
        },
        "Wellfound": {
            "senders": ["wellfound.com", "angel.co"],
            "domains": ["wellfound.com", "angel.co"],
            "keywords": ["wellfound", "angellist talent"],
        },
        "Glassdoor": {
            "senders": ["glassdoor.com", "glassdoormail.com"],
            "domains": ["glassdoor.com"],
            "keywords": ["glassdoor job", "glassdoor alert"],
        },
        "Foundit": {
            "senders": ["foundit.in", "foundit.com", "monsterindia.com"],
            "domains": ["foundit.in", "foundit.com"],
            "keywords": ["foundit"],
        },
        "Cutshort": {
            "senders": ["cutshort.io"],
            "domains": ["cutshort.io"],
            "keywords": ["cutshort"],
        },
        "ZipRecruiter": {
            "senders": ["ziprecruiter.com", "ziprecruitermail.com"],
            "domains": ["ziprecruiter.com"],
            "keywords": ["ziprecruiter"],
        },
        "Greenhouse": {
            "senders": ["greenhouse.io", "ghmail.com"],
            "domains": ["boards.greenhouse.io", "greenhouse.io"],
            "keywords": ["greenhouse.io"],
        },
        "Lever": {
            "senders": ["lever.co", "hire.lever.co"],
            "domains": ["jobs.lever.co", "lever.co"],
            "keywords": ["lever.co"],
        },
        "Workday": {
            "senders": ["myworkday.com", "workday.com"],
            "domains": ["myworkdayjobs.com", "workday.com"],
            "keywords": ["myworkdayjobs"],
        },
    }

    @classmethod
    def register_platform(cls, name: str, senders: List[str], domains: List[str], keywords: Optional[List[str]] = None):
        """Allows dynamically adding new job platforms without modifying existing code."""
        cls.PLATFORM_PATTERNS[name] = {
            "senders": [s.lower() for s in senders],
            "domains": [d.lower() for d in domains],
            "keywords": [k.lower() for k in (keywords or [])],
        }

    @classmethod
    def detect_source(
        cls,
        sender: str,
        subject: str = "",
        body_text: str = "",
        urls: Optional[List[str]] = None,
    ) -> str:
        """Determines the job platform source using multi-signal heuristics."""
        sender_lower = (sender or "").lower()
        subject_lower = (subject or "").lower()
        body_sample = (body_text[:2000] if body_text else "").lower()
        urls = urls or []

        # 1. Check direct sender match
        for platform, rules in cls.PLATFORM_PATTERNS.items():
            for sender_pattern in rules["senders"]:
                if sender_pattern in sender_lower:
                    return platform

        # 2. Check URLs in email
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                for platform, rules in cls.PLATFORM_PATTERNS.items():
                    for domain_pattern in rules["domains"]:
                        if domain_pattern in domain:
                            return platform
            except Exception:
                continue

        # 3. Check keywords in subject and body header
        for platform, rules in cls.PLATFORM_PATTERNS.items():
            for kw in rules["keywords"]:
                if kw in subject_lower or kw in body_sample:
                    return platform

        # 4. Check for company career page indicators
        career_indicators = ["careers@", "recruitment@", "talent@", "jobs@", "hr@"]
        if any(ind in sender_lower for ind in career_indicators):
            return "Company career page"

        # 5. Check for newsletter patterns
        newsletter_indicators = ["newsletter", "digest", "weekly roundup", "dispatch"]
        if any(ind in subject_lower for ind in newsletter_indicators):
            return "Email newsletter"

        return "Other"


source_detector = PlatformSourceDetector()
