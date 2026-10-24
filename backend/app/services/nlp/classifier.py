import re
from typing import Any, Dict, List, Optional, Tuple
from app.core.logging import logger
from app.schemas.nlp import EmailCategory, EmailClassificationResult
from app.services.nlp.adapters import get_llm_adapter


class HybridEmailClassifier:
    """Multi-signal NLP and heuristic email classifier with LLM fallback capabilities."""

    # Categorical keyword and regex signal rules
    SIGNALS: Dict[EmailCategory, Dict[str, Any]] = {
        EmailCategory.OFFER: {
            "patterns": [
                r"\b(job\s+offer|offer\s+letter|offer\s+of\s+employment)\b",
                r"\b(pleased\s+to\s+offer\s+you|delighted\s+to\s+extend\s+an\s+offer)\b",
                r"\b(congratulations\s+on\s+your\s+offer|official\s+offer)\b",
                r"\b(offer\s+details|compensation\s+package)\b",
            ],
            "confidence": 0.95,
            "weight": 10,
        },
        EmailCategory.INTERVIEW: {
            "patterns": [
                r"\b(invitation\s+to\s+interview|schedule\s+(an|your)\s+interview)\b",
                r"\b(interview\s+(invitation|confirmation|details|scheduled))\b",
                r"\b(phone\s+screen|technical\s+interview|coding\s+challenge|first\s+round)\b",
                r"\b(schedule\s+time\s+with\s+(us|me)|calendly\.com|goodtime\.io)\b",
                r"\b(next\s+steps\s+in\s+the\s+interview\s+process)\b",
            ],
            "confidence": 0.92,
            "weight": 9,
        },
        EmailCategory.REJECTION: {
            "patterns": [
                r"\b(unfortunately|regret\s+to\s+inform|not\s+moving\s+forward)\b",
                r"\b(pursue\s+other\s+candidates|decided\s+to\s+move\s+forward\s+with\s+other)\b",
                r"\b(not\s+selected\s+for|will\s+not\s+be\s+proceeding)\b",
                r"\b(keep\s+your\s+resume\s+on\s+file|future\s+opportunities)\b",
                r"\b(at\s+this\s+time,\s+we\s+have\s+decided)\b",
            ],
            "confidence": 0.92,
            "weight": 9,
        },
        EmailCategory.APPLICATION_UPDATE: {
            "patterns": [
                r"\b(thank\s+you\s+for\s+applying|application\s+received)\b",
                r"\b(your\s+application\s+has\s+been\s+received|application\s+status)\b",
                r"\b(we\s+have\s+received\s+your\s+application|successfully\s+applied)\b",
                r"\b(application\s+under\s+review|reviewing\s+your\s+candidacy)\b",
            ],
            "confidence": 0.88,
            "weight": 8,
        },
        EmailCategory.JOB_ALERT: {
            "patterns": [
                r"\b(job\s+alert|new\s+jobs\s+matching|jobs\s+you\s+might\s+like)\b",
                r"\b(recommended\s+jobs|jobs\s+for\s+you|daily\s+job\s+digest)\b",
                r"\b(jobs\s+found\s+for|top\s+job\s+picks|similar\s+jobs)\b",
            ],
            "confidence": 0.85,
            "weight": 7,
        },
        EmailCategory.JOB: {
            "patterns": [
                r"\b(job\s+opportunity|role\s+opening|we\s+are\s+hiring)\b",
                r"\b(position:\s+|job\s+title:|role:\s+)\b",
                r"\b(responsibilities:|requirements:|qualifications:)\b",
                r"\b(apply\s+now|submit\s+your\s+application|view\s+job)\b",
            ],
            "confidence": 0.82,
            "weight": 6,
        },
        EmailCategory.PROMOTION: {
            "patterns": [
                r"\b(boost\s+your\s+career|resume\s+review\s+discount|50%\s+off)\b",
                r"\b(coaching\s+session|webinar\s+registration|enroll\s+today)\b",
                r"\b(premium\s+subscription|upgrade\s+to\s+premium)\b",
            ],
            "confidence": 0.85,
            "weight": 7,
        },
        EmailCategory.NEWSLETTER: {
            "patterns": [
                r"\b(newsletter|weekly\s+edition|issue\s+#\d+|weekly\s+roundup)\b",
                r"\b(tech\s+insights|industry\s+trends|editorial)\b",
            ],
            "confidence": 0.80,
            "weight": 5,
        },
    }

    def classify_with_rules(self, subject: str, sender: str, body: str) -> EmailClassificationResult:
        """Applies multi-signal heuristic evaluation across subject, sender, and body."""
        full_text = f"{subject}\n{sender}\n{body}".lower()
        subject_lower = subject.lower()

        scores: Dict[EmailCategory, Tuple[float, List[str], str]] = {}

        # Evaluate patterns for each category
        for cat, config in self.SIGNALS.items():
            matched_signals = []
            for pattern in config["patterns"]:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    # If match is in the subject line, it carries extra confidence
                    in_subject = bool(re.search(pattern, subject_lower, re.IGNORECASE))
                    matched_signals.append(f"{pattern} (subject={in_subject})")

            if matched_signals:
                weight = config["weight"]
                conf = config["confidence"]
                # Give boost if signal appeared in subject
                if any("subject=True" in s for s in matched_signals):
                    conf = min(0.99, conf + 0.05)
                reason = f"Matched {len(matched_signals)} key signals for {cat.value}."
                scores[cat] = (conf * weight, matched_signals, reason)

        if not scores:
            return EmailClassificationResult(
                category=EmailCategory.OTHER,
                confidence=0.70,
                reason="No career or job related patterns detected in sender, subject, or content.",
                signals_detected=[],
            )

        # Select highest weighted score
        best_cat = max(scores, key=lambda k: scores[k][0])
        _, signals, reason = scores[best_cat]

        return EmailClassificationResult(
            category=best_cat,
            confidence=self.SIGNALS[best_cat]["confidence"],
            reason=f"Heuristic NLP analysis: {reason}",
            signals_detected=signals,
        )

    def classify(self, subject: str, sender: str, body: str) -> EmailClassificationResult:
        """Classifies email using configured LLM adapter with robust rule-based fallback."""
        llm_adapter = get_llm_adapter()

        # Try LLM classification if active
        if llm_adapter:
            try:
                llm_result = llm_adapter.classify_email(subject=subject, sender=sender, body=body)
                if llm_result:
                    return llm_result
            except Exception as e:
                logger.warning("LLM classification failed, falling back to heuristics: %s", str(e))

        # Rule-based / NLP heuristic classification
        return self.classify_with_rules(subject=subject, sender=sender, body=body)


email_classifier = HybridEmailClassifier()
