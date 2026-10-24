import difflib
import re
from typing import Any, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging import logger
from app.schemas.job import DuplicateMatchDetail


# Query parameters commonly used for tracking, analytics, and referrals
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "trk", "trkinfo", "ref", "refid", "trackingid", "fbclid", "gclid",
    "gh_src", "lever-origin", "lever-source", "source", "original_referer",
    "midtoken", "currentjobid", "e", "f", "sid", "sender",
}

# Legal suffixes and generic company corporate terms
COMPANY_SUFFIXES = {
    "inc", "inc.", "llc", "ltd", "ltd.", "pvt", "pvt.", "private", "limited",
    "technologies", "technology", "tech", "solutions", "corp", "corp.",
    "corporation", "group", "co", "co.", "services", "global", "systems",
    "software", "enterprises", "holdings", "international",
}

# Common abbreviations and title aliases
TITLE_SYNONYMS = {
    r"\bsr\.?\b": "senior",
    r"\bjr\.?\b": "junior",
    r"\bswe\b": "software engineer",
    r"\bsde\b": "software engineer",
    r"\bsw eng\.?\b": "software engineer",
    r"\bdev\b": "developer",
    r"\bml\b": "machine learning",
    r"\bai\b": "artificial intelligence",
    r"\bqa\b": "quality assurance",
    r"\bdevops\b": "devops engineer",
    r"\bfrontend\b": "front end",
    r"\bbackend\b": "back end",
    r"\bfullstack\b": "full stack",
}


def normalize_job_url(url: Optional[str]) -> Optional[str]:
    """Strips tracking, referral, and session parameters, fragments, and trailing slashes."""
    if not url or not url.strip():
        return None
    try:
        parsed = urlparse(url.strip())
        if not parsed.netloc:
            return None

        # Filter out tracking query parameters
        filtered_queries = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if k.lower() not in TRACKING_PARAMS
        ]
        # Sort query params for consistent canonical order
        filtered_queries.sort(key=lambda x: x[0].lower())
        new_query = urlencode(filtered_queries)

        # Normalize path: strip trailing slashes unless root
        clean_path = parsed.path.rstrip("/")
        if not clean_path:
            clean_path = "/"

        # Normalize host to lowercase
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Drop fragments and ports 80/443
        clean_url = urlunparse((
            parsed.scheme.lower() or "https",
            netloc,
            clean_path,
            "",
            new_query,
            "",
        ))
        return clean_url
    except Exception as e:
        logger.debug("Failed to normalize URL '%s': %s", url, str(e))
        return url.strip()


def normalize_company_name(name: Optional[str]) -> str:
    """Normalizes company name by stripping legal designations, punctuation, and extra whitespace."""
    if not name:
        return ""
    text = name.lower().strip()
    # Remove bracketed content e.g. (AWS)
    text = re.sub(r"\(.*?\)|\[.*?\]", "", text)
    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    # Strip common corporate suffixes
    filtered = [t for t in tokens if t not in COMPANY_SUFFIXES]
    return " ".join(filtered if filtered else tokens)


def normalize_job_title(title: Optional[str]) -> str:
    """Normalizes job title by resolving standard abbreviations, removing seniority tags/parentheses."""
    if not title:
        return ""
    text = title.lower().strip()
    # Remove requisition codes or parenthesized details e.g. (Remote), (Req-1234), [Hybrid]
    text = re.sub(r"\(.*?\)|\[.*?\]", "", text)
    text = re.sub(r"(?i)\breq(?:uisition)?\s*[-:#]?\s*[a-z0-9]+\b", "", text)
    text = re.sub(r"(?i)\bjob\s*id\s*[-:#]?\s*[a-z0-9]+\b", "", text)
    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # Standardize acronyms and synonyms
    for pattern, replacement in TITLE_SYNONYMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    tokens = text.split()
    return " ".join(tokens)


def token_jaccard_similarity(str1: str, str2: str) -> float:
    """Calculates Jaccard similarity coefficient between token sets of two strings."""
    tokens1: Set[str] = set(str1.lower().split())
    tokens2: Set[str] = set(str2.lower().split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return len(intersection) / len(union)


def string_similarity(str1: str, str2: str) -> float:
    """Combines SequenceMatcher ratio and Jaccard token similarity."""
    if not str1 or not str2:
        return 0.0
    if str1 == str2:
        return 1.0
    seq_ratio = difflib.SequenceMatcher(None, str1, str2).ratio()
    jaccard = token_jaccard_similarity(str1, str2)
    return max(seq_ratio, jaccard)


def calculate_description_similarity(desc1: Optional[str], desc2: Optional[str]) -> float:
    """Calculates TF-IDF cosine similarity between two job descriptions."""
    if not desc1 or not desc2:
        return 0.0
    t1 = desc1.strip()
    t2 = desc2.strip()
    if len(t1) < 40 or len(t2) < 40:
        return token_jaccard_similarity(t1, t2)
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=300)
        tfidf_matrix = vectorizer.fit_transform([t1, t2])
        sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        return sim
    except Exception as e:
        logger.debug("TF-IDF similarity failed: %s", str(e))
        return token_jaccard_similarity(t1, t2)


class DuplicateDetectionEngine:
    """Heuristic and statistical deduplication engine for job postings."""

    def __init__(
        self,
        title_company_threshold: float = 0.85,
        description_threshold: float = 0.60,
    ):
        self.title_company_threshold = title_company_threshold
        self.description_threshold = description_threshold

    def compare_jobs(
        self,
        candidate_url: Optional[str],
        candidate_company: str,
        candidate_title: str,
        candidate_description: Optional[str],
        candidate_location: Optional[str],
        existing_url: Optional[str],
        existing_company: str,
        existing_title: str,
        existing_description: Optional[str],
        existing_location: Optional[str],
    ) -> DuplicateMatchDetail:
        """Compares two job records across multiple dimensions to determine duplication."""
        reasons: List[str] = []

        # 1. Exact Normalized URL Match
        norm_candidate_url = normalize_job_url(candidate_url)
        norm_existing_url = normalize_job_url(existing_url)
        if norm_candidate_url and norm_existing_url and norm_candidate_url == norm_existing_url:
            return DuplicateMatchDetail(
                is_duplicate=True,
                confidence=1.0,
                match_method="EXACT_URL",
                reasons=["Exact match on normalized application URL"],
            )

        # 2. Company + Title Fingerprint
        norm_comp1 = normalize_company_name(candidate_company)
        norm_comp2 = normalize_company_name(existing_company)
        comp_sim = string_similarity(norm_comp1, norm_comp2)

        norm_title1 = normalize_job_title(candidate_title)
        norm_title2 = normalize_job_title(existing_title)
        title_sim = string_similarity(norm_title1, norm_title2)

        if comp_sim >= 0.85 and title_sim >= 0.85:
            # Check location incompatibility if both specify distinct cities
            location_compatible = True
            if candidate_location and existing_location:
                loc1 = candidate_location.lower().strip()
                loc2 = existing_location.lower().strip()
                if loc1 != loc2 and "remote" not in loc1 and "remote" not in loc2:
                    # Dissimilar locations reduce confidence
                    if string_similarity(loc1, loc2) < 0.6:
                        location_compatible = False

            if location_compatible:
                combined_conf = round((comp_sim * 0.45) + (title_sim * 0.55), 3)
                reasons.append(
                    f"Matched company '{existing_company}' ({comp_sim:.0%}) and title '{existing_title}' ({title_sim:.0%})"
                )
                return DuplicateMatchDetail(
                    is_duplicate=True,
                    confidence=combined_conf,
                    match_method="TITLE_COMPANY_FINGERPRINT",
                    reasons=reasons,
                )

        # 3. High Company Similarity + Description Cosine Similarity
        if comp_sim >= 0.75:
            desc_sim = calculate_description_similarity(candidate_description, existing_description)
            if desc_sim >= self.description_threshold:
                conf = round((comp_sim * 0.3) + (desc_sim * 0.7), 3)
                reasons.append(
                    f"Matched company '{existing_company}' ({comp_sim:.0%}) with description similarity ({desc_sim:.0%})"
                )
                return DuplicateMatchDetail(
                    is_duplicate=True,
                    confidence=conf,
                    match_method="DESCRIPTION_SIMILARITY",
                    reasons=reasons,
                )

        return DuplicateMatchDetail(
            is_duplicate=False,
            confidence=0.0,
            match_method=None,
            reasons=[],
        )


deduplication_engine = DuplicateDetectionEngine()
