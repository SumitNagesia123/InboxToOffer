from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging import logger


@dataclass
class MatchEvaluationResult:
    overall_match_score: float
    skill_score: float
    experience_score: float
    semantic_score: float
    matched_skills: List[str]
    missing_required_skills: List[str]
    missing_preferred_skills: List[str]
    explanation_summary: str


class MatchingEngine:
    """Computes explainable, multi-factor compatibility scores between candidate resumes and job postings."""

    def __init__(
        self,
        skill_weight: float = 0.45,
        experience_weight: float = 0.25,
        semantic_weight: float = 0.30,
    ):
        self.skill_weight = skill_weight
        self.experience_weight = experience_weight
        self.semantic_weight = semantic_weight

    def evaluate_skills(
        self,
        candidate_skills: List[str],
        job_required_skills: List[str],
        job_preferred_skills: List[str],
    ) -> Tuple[float, List[str], List[str], List[str]]:
        """Evaluates skill alignment across required and preferred skill taxonomies."""
        candidate_set: Set[str] = {s.lower().strip() for s in candidate_skills}

        matched_skills: List[str] = []
        missing_required: List[str] = []
        missing_preferred: List[str] = []

        # Check required skills
        matched_req_count = 0
        for skill in job_required_skills:
            if skill.lower().strip() in candidate_set:
                matched_req_count += 1
                if skill not in matched_skills:
                    matched_skills.append(skill)
            else:
                missing_required.append(skill)

        # Check preferred skills
        matched_pref_count = 0
        for skill in job_preferred_skills:
            if skill.lower().strip() in candidate_set:
                matched_pref_count += 1
                if skill not in matched_skills:
                    matched_skills.append(skill)
            else:
                missing_preferred.append(skill)

        # Calculate score
        if job_required_skills and job_preferred_skills:
            req_ratio = matched_req_count / len(job_required_skills)
            pref_ratio = matched_pref_count / len(job_preferred_skills)
            score = (0.75 * req_ratio + 0.25 * pref_ratio) * 100.0
        elif job_required_skills:
            req_ratio = matched_req_count / len(job_required_skills)
            score = req_ratio * 100.0
        elif job_preferred_skills:
            pref_ratio = matched_pref_count / len(job_preferred_skills)
            score = pref_ratio * 100.0
        else:
            # If job has no explicit skills listed, compute general overlap
            score = 80.0 if candidate_skills else 50.0

        return round(min(100.0, max(0.0, score)), 1), matched_skills, missing_required, missing_preferred

    def evaluate_experience(
        self,
        candidate_years: Optional[float],
        min_years: Optional[int],
        max_years: Optional[int],
    ) -> float:
        """Compares candidate experience against job requirements."""
        if min_years is None:
            return 100.0

        if candidate_years is None:
            return 50.0

        if candidate_years >= min_years:
            if max_years and candidate_years > (max_years + 4):
                # Mild overqualification adjustment
                return 90.0
            return 100.0

        # Below minimum experience requirement
        ratio = candidate_years / float(min_years)
        score = max(20.0, ratio * 100.0)
        return round(min(100.0, score), 1)

    def evaluate_semantic_relevance(
        self,
        job_title: str,
        job_description: Optional[str],
        resume_text: str,
    ) -> float:
        """Measures topical and domain text relevance between candidate resume and job posting."""
        if not resume_text:
            return 40.0

        job_content = f"{job_title}\n{job_description or ''}".strip()
        if not job_content:
            return 50.0

        # Title alignment bonus
        title_tokens = [t.lower() for t in job_title.split() if len(t) > 3]
        matched_title_tokens = [t for t in title_tokens if t in resume_text.lower()]
        title_factor = (len(matched_title_tokens) / len(title_tokens)) if title_tokens else 0.8

        # TF-IDF Cosine Similarity
        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=350)
            tfidf = vectorizer.fit_transform([job_content, resume_text])
            sim = float(cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0])
        except Exception as e:
            logger.debug("TF-IDF similarity calculation exception: %s", str(e))
            sim = 0.4

        # Combine title and text similarity
        raw_score = (0.4 * title_factor + 0.6 * sim) * 100.0
        # Boost baseline so reasonable matches reflect good match percentages
        scaled_score = min(100.0, max(30.0, raw_score * 1.5))
        return round(scaled_score, 1)

    def generate_explanation(
        self,
        overall_score: float,
        skill_score: float,
        experience_score: float,
        matched_skills: List[str],
        missing_required: List[str],
        missing_preferred: List[str],
        candidate_years: Optional[float],
        min_years: Optional[int],
    ) -> str:
        """Constructs an explainable natural language rationale for the match score."""
        if overall_score >= 80.0:
            rating = "Strong match"
        elif overall_score >= 65.0:
            rating = "Good match"
        elif overall_score >= 50.0:
            rating = "Moderate match"
        else:
            rating = "Low match"

        clauses = [f"{rating} ({overall_score:.1f}%)."]

        # Skill commentary
        if matched_skills:
            clauses.append(f"You match {len(matched_skills)} relevant skills ({', '.join(matched_skills[:4])}).")
        if missing_required:
            clauses.append(f"Missing required skills: {', '.join(missing_required[:3])}.")
        elif missing_preferred:
            clauses.append(f"Missing preferred skills: {', '.join(missing_preferred[:3])}.")

        # Experience commentary
        if min_years is not None and candidate_years is not None:
            if candidate_years >= min_years:
                clauses.append(f"Meets the {min_years}+ years experience requirement ({candidate_years:.1f} yrs).")
            else:
                clauses.append(f"Your experience ({candidate_years:.1f} yrs) is below the requested {min_years} yrs.")

        return " ".join(clauses)

    def calculate_match(
        self,
        candidate_skills: List[str],
        candidate_years: Optional[float],
        resume_text: str,
        job_title: str,
        job_description: Optional[str],
        job_min_exp: Optional[int],
        job_max_exp: Optional[int],
        job_required_skills: List[str],
        job_preferred_skills: List[str],
    ) -> MatchEvaluationResult:
        """Orchestrates comprehensive multi-factor match evaluation."""
        skill_score, matched_skills, missing_req, missing_pref = self.evaluate_skills(
            candidate_skills=candidate_skills,
            job_required_skills=job_required_skills,
            job_preferred_skills=job_preferred_skills,
        )

        exp_score = self.evaluate_experience(
            candidate_years=candidate_years,
            min_years=job_min_exp,
            max_years=job_max_exp,
        )

        semantic_score = self.evaluate_semantic_relevance(
            job_title=job_title,
            job_description=job_description,
            resume_text=resume_text,
        )

        overall = (
            (self.skill_weight * skill_score)
            + (self.experience_weight * exp_score)
            + (self.semantic_weight * semantic_score)
        )
        overall = round(min(100.0, max(0.0, overall)), 1)

        explanation = self.generate_explanation(
            overall_score=overall,
            skill_score=skill_score,
            experience_score=exp_score,
            matched_skills=matched_skills,
            missing_required=missing_req,
            missing_preferred=missing_pref,
            candidate_years=candidate_years,
            min_years=job_min_exp,
        )

        return MatchEvaluationResult(
            overall_match_score=overall,
            skill_score=skill_score,
            experience_score=exp_score,
            semantic_score=semantic_score,
            matched_skills=matched_skills,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            explanation_summary=explanation,
        )


matching_engine = MatchingEngine()
