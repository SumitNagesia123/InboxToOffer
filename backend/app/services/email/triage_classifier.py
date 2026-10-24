import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.services.nlp.adapters import get_llm_adapter


class TriageDecision(str, Enum):
    KEEP = "KEEP"
    DISCARD = "DISCARD"
    UNSURE = "UNSURE"


class TriageCategory(str, Enum):
    # Job categories (KEEP)
    JOB_OPENING_OR_ALERT = "JOB_OPENING_OR_ALERT"
    APPLICATION_CONFIRMATION_OR_STATUS = "APPLICATION_CONFIRMATION_OR_STATUS"
    INTERVIEW_OFFER_OR_REJECTION = "INTERVIEW_OFFER_OR_REJECTION"

    # Reject categories (DISCARD)
    FINANCIAL_SPAM = "FINANCIAL_SPAM"
    COMMERCE_ORDER = "COMMERCE_ORDER"
    OTP_SECURITY = "OTP_SECURITY"
    COURSE_PROMO = "COURSE_PROMO"
    PERSONAL = "PERSONAL"
    OTHER_NON_JOB = "OTHER_NON_JOB"

    # Low-confidence fallback (KEEP)
    UNSURE = "UNSURE"


class TriageResult(BaseModel):
    category: TriageCategory = Field(..., description="Determined classification category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reason: str = Field(..., description="One short sentence explaining the classification decision")
    decision: TriageDecision = Field(..., description="Actionable decision: KEEP, DISCARD, or UNSURE")
    should_keep: bool = Field(..., description="True if email should be kept/stored; False only if confident discard")


# Default threshold required to discard an email (bias heavily toward keeping real jobs)
DEFAULT_DISCARD_CONFIDENCE_THRESHOLD = 0.85

from app.core.email_filter_config import EXCLUDED_DOMAINS, JOB_PLATFORM_DOMAINS

JOB_DOMAINS = set(JOB_PLATFORM_DOMAINS)
COMMERCE_DOMAINS = set(EXCLUDED_DOMAINS)

TRAVEL_DOMAINS = {
    "makemytrip.com",
    "zen-makemytrip.com",
    "uber.com",
    "ola.cabs",
    "irctc.co.in",
    "goibibo.com",
    "ixigo.com",
    "easemytrip.com",
    "redbus.in",
    "agoda.com",
    "booking.com",
    "airindia.com",
    "indigo.in",
}

COURSE_DOMAINS = {
    "alison.com",
    "eduskillsfoundation.org",
    "springboard.infosys.com",
    "udemy.com",
    "coursera.org",
    "simplilearn.com",
    "scaler.com",
    "upgrad.com",
    "codingninjas.com",
}

MARKETING_NEWSLETTER_DOMAINS = {
    "openrouter.ai",
    "lamatic.ai",
    "labs.lamatic.ai",
    "google.com",
}

FINANCIAL_PATTERNS = [
    r"\b(credit\s+card|tata\s+neu\s+card|rupay\s+card|visa\s+card|kiwi\s+rupay|virtual\s+card)\b",
    r"\b(pre-approved\s+loan|personal\s+loan|instant\s+credit|loan\s+approved|rupay\s+application)\b",
    r"\b(cibil\s+score|credit\s+score|hdfc\s+bank|icici\s+bank|sbi\s+card|axis\s+bank)\b",
    r"\b(debit\s+alert|statement\s+of\s+account|card\s+application\s+is\s+incomplete)\b",
]

TRAVEL_PATTERNS = [
    r"\b(unmissable\s+deals\s+on\s+flights|deals\s+on\s+international\s+flights|international\s+flights)\b",
    r"\b(train\s+tickets\s+on\s+uber|train\s+tickets?|metro\s+ticket|flight\s+booking|booking\s+confirmed)\b",
    r"\b(air\s+tickets?|bike\s+saver|off\s+your\s+next\s+\d+\s+trips|travel\s+deals?|bus\s+tickets?)\b",
]

COMMERCE_PATTERNS = [
    r"\b(delivered:\s+|out\s+for\s+delivery|order\s+confirmed|shipped:\s+)\b",
    r"\b(package\s+arrived|shipment\s+update|tracking\s+number|return\s+picked\s+up)\b",
    r"\b(your\s+amazon(\.in|\.com)?\s+order|your\s+flipkart\s+order|regarding\s+your\s+recent\s+order)\b",
    r"\b(the\s+westside\s+way|denim,\s+the\s+westside|don't\s+start\s+shopping|tatacliq|tata\s+cliq)\b",
    r"\b(mark\s+the\s+date\.\s+thank\s+us\s+later|run\s+for\s+rewards|your\s+other\s+look\s+just\s+called)\b",
]

OTP_SECURITY_PATTERNS = [
    r"\b(confirm\s+your\s+identity|one\s+time\s+password|your\s+otp\s+is)\b",
    r"\b(verification\s+code|verify\s+your\s+email|security\s+alert|login\s+detected)\b",
    r"\b(password\s+reset|reset\s+your\s+password|2-step\s+verification)\b",
]

COURSE_PROMO_PATTERNS = [
    r"\b(power\s+bi\s+dashboard\s+from\s+scratch|masterclass|webinar\s+registration|webinar)\b",
    r"\b(enroll\s+today|free\s+demo\s+class|flat\s+\d+%\s+off\s+on\s+all\s+courses|our\s+sale\s+starts\s+now)\b",
    r"\b(bootcamp\s+batch|become\s+a\s+certified|learn\s+data\s+science\s+in\s+\d+)\b",
    r"\b(upgrade\s+your\s+skills|career\s+transition\s+program|free\s+workshop|in-demand\s+skills)\b",
    r"\b(udemy\s+course\s+access|udemy\s+course|shape\s+your\s+future|batch\s+starts|build\s+ai\s+with)\b",
    r"\b(free\s+live\s+placement\s+session|online\s+learning|certification\s+course|eduskills|springboard)\b",
]

TECH_NEWSLETTER_PATTERNS = [
    r"\b(try\s+gemini|gemini\s+\d+|early\s+access:\s+try|when\s+ai\s+agents\s+go\s+wrong|traibe)\b",
    r"\b(iso\s+27001|security\s+certification|tool\s+calling:\s+one\s+pattern|stop\s+writing\s+code\s+that\s+repairs)\b",
    r"\b(move\s+your\s+model\s+config|gitlab’s\s+first\s+india\s+office|how\s+are\s+you\s+really\s+feeling)\b",
]

SECURITY_ANTIVIRUS_PATTERNS = [
    r"\b(mcafee|norton|avast|bitdefender|kaspersky)\b",
    r"\b(no\s+longer\s+have\s+all-in-one\s+protection|antivirus\s+expired|subscription\s+expired)\b",
]

JOB_ALERT_PATTERNS = [
    r"\b(\d+\+?\s+jobs?\s+(matching|recommended|for\s+you)|curated\s+jobs|job\s+alert)\b",
    r"\b(daily\s+job\s+digest|new\s+jobs?\s+in|jobs?\s+you\s+might\s+like|role\s+opening)\b",
    r"\b(hiring\s+for|we\s+are\s+hiring|top\s+it\/tech\s+jobs|urgent\s+hiring)\b",
    r"\b(apply\s+now\s+to|apply\s+now|job\s+recommendations?|job\s+opportunity)\b",
    r"\b(internship\s+programme|careers?@|placement\s+session|fresh\s+jobs)\b",
]

JOB_STATUS_PATTERNS = [
    r"\b(application\s+for\s+[a-z0-9\s\-]+|thank\s+you\s+for\s+applying)\b",
    r"\b(your\s+recent\s+job\s+application|application\s+received|application\s+submitted)\b",
    r"\b(application\s+status|reviewing\s+your\s+candidacy|under\s+review)\b",
    r"\b(application\s+successful|applied\s+successfully|application\s+acknowledged)\b",
]

JOB_INTERVIEW_OFFER_PATTERNS = [
    r"\b(invitation\s+to\s+interview|interview\s+scheduled|schedule\s+your\s+interview)\b",
    r"\b(technical\s+round|coding\s+assessment|phone\s+screen|shortlisted\s+for)\b",
    r"\b(job\s+offer|offer\s+of\s+employment|offer\s+letter|pleased\s+to\s+offer)\b",
    r"\b(regret\s+to\s+inform|not\s+moving\s+forward|decided\s+to\s+pursue\s+other)\b",
]


def classify_email_triage(
    sender: str,
    subject: str,
    snippet: str = "",
    body: str = "",
    discard_threshold: float = DEFAULT_DISCARD_CONFIDENCE_THRESHOLD,
) -> TriageResult:
    """
    Evaluates whether an email belongs to recruitment/career workflows or should be discarded.
    Bias is strictly toward keeping emails (only discards if confident >= discard_threshold).
    """
    sender_clean = (sender or "").lower().strip()
    subject_clean = (subject or "").lower().strip()
    content_clean = f"{subject_clean}\n{snippet.lower()}\n{body[:2000].lower()}"

    # Extract domain from sender
    sender_domain = ""
    domain_match = re.search(r"@([a-z0-9\-\.]+)", sender_clean)
    if domain_match:
        sender_domain = domain_match.group(1).lstrip("www.")

    # 1. Immediate positive check: Known Recruitment/Job Portals
    job_platform_names = ["linkedin", "internshala", "hirist", "naukri", "foundit", "indeed", "wellfound", "instahyre", "acciojob", "greenhouse", "lever", "workday", "smartrecruiters", "ashby"]
    is_job_sender = any(jd in sender_domain for jd in JOB_DOMAINS) or any(name in sender_clean for name in job_platform_names)

    if is_job_sender:
        if any(re.search(pat, content_clean) for pat in JOB_INTERVIEW_OFFER_PATTERNS):
            return TriageResult(
                category=TriageCategory.INTERVIEW_OFFER_OR_REJECTION,
                confidence=0.96,
                reason="Recruitment interview schedule, job offer, or application decision.",
                decision=TriageDecision.KEEP,
                should_keep=True,
            )
        if any(re.search(pat, content_clean) for pat in JOB_STATUS_PATTERNS):
            return TriageResult(
                category=TriageCategory.APPLICATION_CONFIRMATION_OR_STATUS,
                confidence=0.94,
                reason="Job application acknowledgement, candidate review status, or confirmation.",
                decision=TriageDecision.KEEP,
                should_keep=True,
            )
        return TriageResult(
            category=TriageCategory.JOB_OPENING_OR_ALERT,
            confidence=0.95,
            reason="Structured job opening, recruiter alert, or role recommendation from verified job portal.",
            decision=TriageDecision.KEEP,
            should_keep=True,
        )

    # 2. Check Travel, Flights & Commute (MakeMyTrip, Uber, IRCTC, etc.)
    is_travel_domain = any(td in sender_domain for td in TRAVEL_DOMAINS)
    if is_travel_domain or any(re.search(pat, content_clean) for pat in TRAVEL_PATTERNS):
        conf = 0.98 if is_travel_domain else 0.94
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.COMMERCE_ORDER,
            confidence=conf,
            reason="Travel booking, flight ticket promotion, or ride service update.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 3. Check Commerce Orders (Amazon, Swiggy, Flipkart, Tata CLiQ delivery updates)
    is_commerce_domain = any(cd in sender_domain for cd in COMMERCE_DOMAINS)
    if is_commerce_domain or any(re.search(pat, content_clean) for pat in COMMERCE_PATTERNS):
        conf = 0.98 if is_commerce_domain else 0.92
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.COMMERCE_ORDER,
            confidence=conf,
            reason="E-commerce shipment, package delivery, or commercial purchase order.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 4. Check Financial Spam & Cards (e.g., Tata Neu card, Kiwi Rupay, personal loans)
    if any(re.search(pat, content_clean) for pat in FINANCIAL_PATTERNS):
        conf = 0.96
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.FINANCIAL_SPAM,
            confidence=conf,
            reason="Financial promotion, credit card offer, or personal loan advertisement.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 5. Check Course, Bootcamp & Academy Promos (e.g. Alison, EduSkills, Infosys Springboard, Udemy)
    is_course_domain = any(cd in sender_domain for cd in COURSE_DOMAINS)
    if is_course_domain or any(re.search(pat, content_clean) for pat in COURSE_PROMO_PATTERNS):
        conf = 0.96 if is_course_domain else 0.93
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.COURSE_PROMO,
            confidence=conf,
            reason="Commercial training course, paid bootcamp, skill platform, or webinar promotion.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 6. Check Tech Newsletters & Corporate Marketing (e.g. Google AI Pro, OpenRouter, Lamatic, Talent500 community webinars)
    is_newsletter_domain = any(nd in sender_domain for nd in MARKETING_NEWSLETTER_DOMAINS)
    if (
        (is_newsletter_domain and not is_job_sender)
        or any(re.search(pat, content_clean) for pat in TECH_NEWSLETTER_PATTERNS)
        or ("talent500" in sender_clean and ("community" in sender_clean or "hello@" in sender_clean or "when ai agents go wrong" in subject_clean or "traibe" in content_clean))
        or ("google ai pro" in sender_clean or "gemini" in subject_clean)
        or ("aman sharma" in sender_clean and "lamatic" in content_clean)
    ):
        conf = 0.95
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.OTHER_NON_JOB,
            confidence=conf,
            reason="Technology marketing newsletter, corporate announcement, or community webinar.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 7. Check Antivirus & Non-Job Software Subscriptions (e.g. McAfee)
    if any(re.search(pat, content_clean) for pat in SECURITY_ANTIVIRUS_PATTERNS):
        conf = 0.96
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.OTHER_NON_JOB,
            confidence=conf,
            reason="Antivirus or subscription renewal marketing.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 8. Check Pure OTP / Security verification codes
    if any(re.search(pat, content_clean) for pat in OTP_SECURITY_PATTERNS):
        conf = 0.93
        should_discard = conf >= discard_threshold
        return TriageResult(
            category=TriageCategory.OTP_SECURITY,
            confidence=conf,
            reason="Account authentication, OTP, or identity confirmation notice.",
            decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
            should_keep=not should_discard,
        )

    # 7. Check Genuine Job Categories
    # A. Interview, Offer, or Rejection
    if any(re.search(pat, content_clean) for pat in JOB_INTERVIEW_OFFER_PATTERNS):
        return TriageResult(
            category=TriageCategory.INTERVIEW_OFFER_OR_REJECTION,
            confidence=0.96,
            reason="Recruitment interview schedule, job offer, or application decision.",
            decision=TriageDecision.KEEP,
            should_keep=True,
        )

    # B. Job Application Status / Confirmation
    if any(re.search(pat, content_clean) for pat in JOB_STATUS_PATTERNS):
        return TriageResult(
            category=TriageCategory.APPLICATION_CONFIRMATION_OR_STATUS,
            confidence=0.94,
            reason="Job application acknowledgement, candidate review status, or confirmation.",
            decision=TriageDecision.KEEP,
            should_keep=True,
        )

    # C. Job Alerts & Openings
    if is_job_sender or any(re.search(pat, content_clean) for pat in JOB_ALERT_PATTERNS):
        conf = 0.95 if is_job_sender else 0.88
        return TriageResult(
            category=TriageCategory.JOB_OPENING_OR_ALERT,
            confidence=conf,
            reason="Structured job opening, recruiter alert, or role recommendation.",
            decision=TriageDecision.KEEP,
            should_keep=True,
        )

    # 8. Borderline / Ambiguous: Optional LLM verification if adapter is available
    try:
        adapter = get_llm_adapter()
        if adapter:
            llm_res = adapter.classify_email(subject=subject, sender=sender, body=body or snippet)
            if llm_res and llm_res.category:
                cat_val = llm_res.category.value
                if cat_val in ("JOB", "JOB_ALERT"):
                    return TriageResult(
                        category=TriageCategory.JOB_OPENING_OR_ALERT,
                        confidence=min(1.0, float(llm_res.confidence or 0.88)),
                        reason=llm_res.reason or "Classified by AI LLM as job alert/posting.",
                        decision=TriageDecision.KEEP,
                        should_keep=True,
                    )
                elif cat_val in ("APPLICATION_UPDATE", "APPLICATION_ACK"):
                    return TriageResult(
                        category=TriageCategory.APPLICATION_CONFIRMATION_OR_STATUS,
                        confidence=min(1.0, float(llm_res.confidence or 0.88)),
                        reason=llm_res.reason or "Classified by AI LLM as application status.",
                        decision=TriageDecision.KEEP,
                        should_keep=True,
                    )
                elif cat_val in ("INTERVIEW", "OFFER", "REJECTION"):
                    return TriageResult(
                        category=TriageCategory.INTERVIEW_OFFER_OR_REJECTION,
                        confidence=min(1.0, float(llm_res.confidence or 0.90)),
                        reason=llm_res.reason or "Classified by AI LLM as interview, offer, or decision.",
                        decision=TriageDecision.KEEP,
                        should_keep=True,
                    )
                elif cat_val in ("ADVERTISEMENT", "PROMOTION", "OTHER"):
                    conf = min(1.0, float(llm_res.confidence or 0.85))
                    should_discard = conf >= discard_threshold
                    return TriageResult(
                        category=TriageCategory.OTHER_NON_JOB,
                        confidence=conf,
                        reason=llm_res.reason or "Classified by AI LLM as commercial or non-job content.",
                        decision=TriageDecision.DISCARD if should_discard else TriageDecision.UNSURE,
                        should_keep=not should_discard,
                    )
    except Exception as llm_err:
        logger.warning("LLM triage classification fallback failed or timed out: %s. Safely keeping email.", str(llm_err))

    # 9. Unsure Fallback: Keep the email to protect the candidate from lost opportunities
    return TriageResult(
        category=TriageCategory.UNSURE,
        confidence=0.50,
        reason="Uncertain career signals; retained and flagged for candidate safety.",
        decision=TriageDecision.UNSURE,
        should_keep=True,
    )


# Reusable alias requested by interface contract
classifyEmail = classify_email_triage

