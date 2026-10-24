import pytest
from app.services.email.triage_classifier import (
    classify_email_triage,
    TriageCategory,
    TriageDecision,
)
from app.core.email_filter_config import build_x_gm_raw_query


SAMPLE_TEST_EMAILS = [
    # 1. Job Alert / Digest (Hirist)
    ("hirist.com", "10+ Jobs Matching Your Profile", "Jobs recommended for you Full Stack Developer", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 2. Direct Job Opening (Hirist tech)
    ("hirist.tech", "Data Scientist @ GREAT LEARNING EDUCATION SERVICES", "Great Learning is hiring for Data Scientist", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 3. Foundit Job Recommendations
    ("Vanya from foundit", "3 jobs that you haven't applied yet but others are applying", "3 new jobs from Meeras Resource", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 4. Acciojob curated jobs
    ("placement@acciojob-team.com", "daily curated jobs for you", "Jobs curated for software engineers", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 5. Internshala alert
    ("Internshala", "New web development internships matching your preferences", "Apply to 5 new internships", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 6. LinkedIn job alert
    ("jobalerts-noreply@linkedin.com", "30+ new jobs for 'Software Engineer' in Bengaluru", "LinkedIn Job Alert for your saved search", TriageCategory.JOB_OPENING_OR_ALERT, TriageDecision.KEEP),
    # 7. Job Application Status (EXL)
    ("EXL-Fusion-Notification", "Your recent job application for Data Analyst - 18760", "We have received your application for Data Analyst", TriageCategory.APPLICATION_CONFIRMATION_OR_STATUS, TriageDecision.KEEP),
    # 8. Greenhouse application acknowledgement
    ("no-reply@greenhouse.io", "Thank you for applying to Stripe", "Your application has been received and is under review", TriageCategory.APPLICATION_CONFIRMATION_OR_STATUS, TriageDecision.KEEP),
    # 9. Interview Invitation
    ("talent@techcorp.com", "Invitation to Interview: Senior Backend Engineer", "We would like to schedule a technical round with our team", TriageCategory.INTERVIEW_OFFER_OR_REJECTION, TriageDecision.KEEP),
    # 10. Official Job Offer
    ("hr@globaltech.com", "Official Job Offer - Software Engineer", "We are pleased to offer you the position of Software Engineer", TriageCategory.INTERVIEW_OFFER_OR_REJECTION, TriageDecision.KEEP),
    # 11. Polite Job Rejection
    ("recruiting@startup.io", "Update on your application with Startup", "Unfortunately we have decided to pursue other candidates at this time", TriageCategory.INTERVIEW_OFFER_OR_REJECTION, TriageDecision.KEEP),
    
    # 12. Financial Spam (Tata Neu card application)
    ("Connect <noreply@connect.in>", "Hi sumitnagesia826 - Register your Tata Neu Card Application", "Your Application for Tata Neu card is incomplete", TriageCategory.FINANCIAL_SPAM, TriageDecision.DISCARD),
    # 13. Pre-approved Loan spam
    ("loans@creditbazaar.com", "Pre-approved personal loan of Rs 5,00,000 waiting for you", "Check your CIBIL score and get instant credit", TriageCategory.FINANCIAL_SPAM, TriageDecision.DISCARD),
    # 14. E-commerce Delivery (Amazon)
    ("Amazon.in <shipment-tracking@amazon.in>", "Delivered: SELLORIA Brand Soft Cotton...", "Your package was delivered to resident", TriageCategory.COMMERCE_ORDER, TriageDecision.DISCARD),
    # 15. E-commerce Out for Delivery (Amazon)
    ("Amazon.in <order-update@amazon.in>", "Out for delivery: SELLORIA Brand Soft Cotton...", "Your Amazon order is arriving today", TriageCategory.COMMERCE_ORDER, TriageDecision.DISCARD),
    # 16. Swiggy Food Delivery promo
    ("Swiggy <noreply@swiggy.in>", "Zero fees. Zero regrets. Order dinner now", "Flat 50% off on your favorite restaurants", TriageCategory.COMMERCE_ORDER, TriageDecision.DISCARD),
    # 17. Security / OTP alert (Google)
    ("Google <no-reply@accounts.google.com>", "Security alert for your linked Google account", "New sign-in detected on Windows device", TriageCategory.OTP_SECURITY, TriageDecision.DISCARD),
    # 18. Antivirus Subscription alert (McAfee)
    ("McAfee <mcafee@email.mcafee.com>", "You no longer have all-in-one protection.", "Your McAfee protection has ended! Renew now", TriageCategory.OTHER_NON_JOB, TriageDecision.DISCARD),
    # 19. Course / Bootcamp promotion (Anjali Pandey Power BI)
    ("Anjali Pandey | Data Scientist", "Can You Build a Power BI Dashboard from Scratch? Learn Power Query", "Join our free masterclass and webinar today", TriageCategory.COURSE_PROMO, TriageDecision.DISCARD),
    # 20. Dating app commercial notification (Hinge)
    ("Hinge Team <hello@hinge.co>", "Your HingeX offer expires soon", "Exclusive dating membership offer", TriageCategory.COMMERCE_ORDER, TriageDecision.DISCARD),
    # 21. Truly ambiguous career-adjacent note (Unsure / Protected)
    ("John Doe <john.doe@company.org>", "Catching up on project updates and next steps", "Let us sync on the deliverables tomorrow.", TriageCategory.UNSURE, TriageDecision.UNSURE),
]


def test_triage_classifier_twenty_samples():
    """Validates the triage classifier across all 20 benchmark test scenarios."""
    for sender, subject, snippet, expected_cat, expected_decision in SAMPLE_TEST_EMAILS:
        res = classify_email_triage(sender=sender, subject=subject, snippet=snippet)
        assert res.decision == expected_decision, (
            f"Failed on '{subject}': expected decision {expected_decision}, got {res.decision} ({res.category}, conf={res.confidence})"
        )
        assert res.confidence >= 0.0 and res.confidence <= 1.0
        assert len(res.reason) > 5


def test_triage_classifier_safe_fallback_on_llm_error(monkeypatch):
    """Ensures that if an external LLM fails or times out, the classifier safely falls back to KEEP (UNSURE)."""
    # Simulate LLM raising an unexpected network timeout
    def mock_get_adapter():
        class BrokenAdapter:
            def classify_email(self, *args, **kwargs):
                raise RuntimeError("Simulated upstream network connection timeout")
        return BrokenAdapter()

    monkeypatch.setattr("app.services.email.triage_classifier.get_llm_adapter", mock_get_adapter)

    res = classify_email_triage(
        sender="ambiguous.contact@example.com",
        subject="Notes from our meeting earlier today",
        snippet="Let's follow up tomorrow.",
    )
    assert res.decision == TriageDecision.UNSURE
    assert res.should_keep is True


def test_x_gm_raw_query_builder():
    """Validates that the Gmail query pre-filter string contains domain ORs and exclusion denylists."""
    query = build_x_gm_raw_query(since_days=30)
    assert "from:linkedin.com" in query
    assert "from:internshala.com" in query
    assert "from:hirist.com" in query
    assert "-from:amazon.in" in query
    assert "-from:swiggy.in" in query
    assert "after:" in query
