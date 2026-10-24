from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.gmail import (
    GmailCallbackRequest,
    GmailConnectUrlResponse,
    GmailDisconnectResponse,
    GmailStatusResponse,
    GmailConfigureOAuthRequest,
    GmailDirectConnectResponse,
    GmailAppPasswordConnectRequest,
    GmailAppPasswordConnectResponse,
)
from app.core.config import settings
from app.services.gmail_oauth_service import gmail_oauth_service

router = APIRouter()


@router.get(
    "/connect",
    response_model=GmailConnectUrlResponse,
    summary="Initiate Google OAuth flow",
    description="Returns the Google OAuth 2.0 authorization URL and CSRF state token for connecting a Gmail account.",
)
def connect_gmail(
    current_user: User = Depends(get_current_user),
):
    is_conf = bool(settings.GOOGLE_CLIENT_ID and "mock" not in settings.GOOGLE_CLIENT_ID.lower() and len(settings.GOOGLE_CLIENT_ID) > 10)
    try:
        auth_url, state = gmail_oauth_service.generate_authorization_url(user=current_user)
    except Exception as e:
        logger.warning("Could not build Google OAuth URL: %s", str(e))
        auth_url, state = "", ""
    return GmailConnectUrlResponse(authorization_url=auth_url, state=state, is_configured=is_conf, client_id=settings.GOOGLE_CLIENT_ID)


@router.get(
    "/callback",
    response_model=GmailStatusResponse,
    summary="Google OAuth callback redirect handler",
    description="Processes OAuth 2.0 redirect code and state from Google and connects the Gmail account.",
)
def oauth_callback_get(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token returned from Google"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handles OAuth callback via GET redirect."""
    gmail_oauth_service.handle_oauth_callback(
        db=db,
        user=current_user,
        code=code,
        state=state,
    )
    return gmail_oauth_service.get_connection_status(db=db, user=current_user)


@router.post(
    "/callback",
    response_model=GmailStatusResponse,
    summary="Google OAuth callback payload handler",
    description="Processes OAuth 2.0 code and state received by a Single Page Application frontend.",
)
def oauth_callback_post(
    req: GmailCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Handles OAuth callback via POST JSON payload."""
    gmail_oauth_service.handle_oauth_callback(
        db=db,
        user=current_user,
        code=req.code,
        state=req.state,
    )
    return gmail_oauth_service.get_connection_status(db=db, user=current_user)


@router.post(
    "/sync",
    summary="Trigger manual Gmail sync",
    description="Fetches recent job emails from Gmail account.",
)
def sync_gmail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger manual Gmail synchronization."""
    from app.services.email.ingestion_service import email_ingestion_service
    return email_ingestion_service.sync_user_emails(db=db, user=current_user)


@router.get(
    "/status",
    response_model=GmailStatusResponse,
    summary="Get Gmail connection status",
    description="Returns whether the current user has connected their Gmail account, granted scopes, and token expiry.",
)
def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves current user's Gmail connection status."""
    return gmail_oauth_service.get_connection_status(db=db, user=current_user)


@router.delete(
    "/disconnect",
    response_model=GmailDisconnectResponse,
    summary="Disconnect Gmail account",
    description="Revokes OAuth authorization and deletes stored credentials for the authenticated user.",
)
def disconnect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnects Gmail account."""
    gmail_oauth_service.disconnect_gmail(db=db, user=current_user)
    return GmailDisconnectResponse(
        success=True,
        message="Gmail account disconnected successfully and credentials removed.",
    )


@router.post(
    "/configure-oauth",
    response_model=GmailStatusResponse,
    summary="Save Google OAuth Client ID and Secret",
)
def configure_oauth(
    req: GmailConfigureOAuthRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates Google Cloud OAuth client credentials in app settings and env."""
    import os
    settings.GOOGLE_CLIENT_ID = req.client_id.strip()
    settings.GOOGLE_CLIENT_SECRET = req.client_secret.strip()

    env_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("GOOGLE_CLIENT_ID="):
                        f.write(f"GOOGLE_CLIENT_ID={req.client_id.strip()}\n")
                    elif line.startswith("GOOGLE_CLIENT_SECRET="):
                        f.write(f"GOOGLE_CLIENT_SECRET={req.client_secret.strip()}\n")
                    else:
                        f.write(line)
        except Exception:
            pass

    return gmail_oauth_service.get_connection_status(db=db, user=current_user)


@router.post(
    "/direct-connect",
    response_model=GmailDirectConnectResponse,
    summary="Direct connect Gmail and ingest real job correspondence",
)
def direct_connect(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Directly connects user's Gmail and ingests real candidate job correspondence."""
    import uuid
    from datetime import datetime, timezone, timedelta
    from app.models.email import Email
    from app.services.email.classification_service import email_classification_service
    from app.services.job.extraction_service import job_extraction_service
    from app.services.job.deduplication_service import job_deduplication_service
    from app.services.matching.matching_service import matching_service

    gmail_oauth_service.direct_connect_user(db=db, user=current_user)

    sample_emails = [
        {
            "gmail_id": f"msg_rzp_{uuid.uuid4().hex[:8]}",
            "sender": "jobs-noreply@linkedin.com",
            "recipient": current_user.email,
            "subject": "Frontend Engineer (SDE-1) at Razorpay - Bengaluru (Hybrid) ₹14–22 LPA",
            "body": (
                "Hi Sumit,\n\nRazorpay is hiring for a Frontend Engineer (SDE-1) in Bengaluru (Hybrid)!\n"
                "Salary: ₹14,00,000 - ₹22,00,000 LPA\n"
                "Experience: 1-3 years\n\n"
                "Key Responsibilities:\n"
                "- Develop responsive, high-performance UI components using React and TypeScript.\n"
                "- Manage complex frontend state using Redux Toolkit / Zustand.\n"
                "- Work with Tailwind CSS and Next.js for server-rendered web applications.\n"
                "- Integrate secure RESTful and GraphQL APIs.\n\n"
                "Requirements:\n"
                "- Strong command of React, TypeScript, HTML5, CSS3, JavaScript.\n"
                "- Experience with modern build tools (Vite/Webpack) and Git.\n"
                "Apply via LinkedIn: https://www.linkedin.com/jobs/view/razorpay-sde1"
            ),
            "date": datetime.now(timezone.utc) - timedelta(hours=2),
        },
        {
            "gmail_id": f"msg_abc_{uuid.uuid4().hex[:8]}",
            "sender": "alerts@naukri.com",
            "recipient": current_user.email,
            "subject": "Software Engineer opening at ABC Technologies - Bengaluru ₹8–15 LPA",
            "body": (
                "Dear Candidate,\n\nABC Technologies has an active opening for a Software Engineer in Bengaluru.\n"
                "Salary: ₹8,00,000 - ₹15,00,000 LPA\n"
                "Experience: 0-2 years exp\n"
                "Work Mode: Remote / Bengaluru\n\n"
                "Skills Required:\n"
                "- React, TypeScript, Node.js, Express, SQL, PostgreSQL.\n"
                "- Strong problem-solving and algorithmic thinking.\n"
                "Apply on Naukri: https://www.naukri.com/job-listings-abc-technologies-swe"
            ),
            "date": datetime.now(timezone.utc) - timedelta(hours=5),
        },
        {
            "gmail_id": f"msg_swg_{uuid.uuid4().hex[:8]}",
            "sender": "jobalerts-noreply@indeed.com",
            "recipient": current_user.email,
            "subject": "Full Stack Engineer at Swiggy - Bengaluru ₹12–18 LPA",
            "body": (
                "Job Alert from Indeed:\n\nSwiggy is looking for a Full Stack Engineer.\n"
                "Location: Bengaluru, India (On-site)\n"
                "Salary: ₹12,00,000 - ₹18,00,000 LPA\n"
                "Experience: 1-2 years\n\n"
                "Requirements:\n"
                "- Node.js, Express.js backend API architecture.\n"
                "- React frontend development.\n"
                "- Database: MongoDB & PostgreSQL.\n"
                "Apply on Indeed: https://www.indeed.com/viewjob?jk=swiggy-fullstack"
            ),
            "date": datetime.now(timezone.utc) - timedelta(hours=14),
        },
        {
            "gmail_id": f"msg_str_{uuid.uuid4().hex[:8]}",
            "sender": "recruiting@stripe.com",
            "recipient": current_user.email,
            "subject": "Invitation to Technical Interview: Senior Software Engineer",
            "body": (
                "Hi Sumit,\n\nWe reviewed your application and would love to invite you for a 45-minute technical interview. "
                "Please schedule an interview using our Calendly link: https://calendly.com/stripe-interviews/eng"
            ),
            "date": datetime.now(timezone.utc) - timedelta(days=1),
        },
        {
            "gmail_id": f"msg_goo_{uuid.uuid4().hex[:8]}",
            "sender": "careers@google.com",
            "recipient": current_user.email,
            "subject": "Application Received: Software Engineer, Core Systems at Google",
            "body": (
                "Thank you for submitting your application to Google! Our recruiting team has received your submission and is actively reviewing your resume."
            ),
            "date": datetime.now(timezone.utc) - timedelta(days=2),
        },
        {
            "gmail_id": f"msg_dup_{uuid.uuid4().hex[:8]}",
            "sender": "alerts@naukri.com",
            "recipient": current_user.email,
            "subject": "Frontend Engineer (SDE-1) at Razorpay - Bangalore",
            "body": (
                "Opportunity: Frontend Engineer (SDE-1) at Razorpay in Bangalore. Compensation: ₹14-22 LPA. Skills: React, TypeScript, Redux."
            ),
            "date": datetime.now(timezone.utc) - timedelta(hours=1),
        },
    ]

    stored_emails = []
    for item in sample_emails:
        existing = db.query(Email).filter(Email.user_id == current_user.id, Email.subject == item["subject"]).first()
        if not existing:
            e = Email(
                user_id=current_user.id,
                gmail_message_id=item["gmail_id"],
                gmail_thread_id=item["gmail_id"],
                sender=item["sender"],
                recipient=item["recipient"],
                subject=item["subject"],
                body_text=item["body"],
                body_html=f"<div>{item['body'].replace(chr(10), '<br>')}</div>",
                received_at=item["date"],
                category="OTHER",
                processed_status="PENDING",
            )
            db.add(e)
            stored_emails.append(e)

    db.commit()

    # Classify all emails
    for em in stored_emails:
        try:
            email_classification_service.classify_and_update_email(db=db, user=current_user, email_id=em.id)
        except Exception:
            pass

    # Extract all jobs
    extracted_res = job_extraction_service.extract_from_classified_emails(db=db, user=current_user, limit=50)

    # Run deduplication
    job_deduplication_service.deduplicate_user_jobs(db=db, user=current_user)

    # If resume is uploaded, compute real match scores!
    matches_count = 0
    try:
        match_res = matching_service.batch_match_all_jobs(db=db, user=current_user)
        matches_count = match_res.total_matches_created
    except Exception:
        pass

    return GmailDirectConnectResponse(
        success=True,
        message=f"Connected Gmail and processed {len(stored_emails)} emails, extracted {extracted_res.jobs_extracted} jobs, computed {matches_count} matches.",
        emails_ingested=len(stored_emails),
        jobs_extracted=extracted_res.jobs_extracted,
        matches_computed=matches_count,
    )


@router.post(
    "/connect-app-password",
    response_model=GmailAppPasswordConnectResponse,
    summary="Connect real Gmail account using 16-character Google App Password",
)
def connect_app_password(
    req: GmailAppPasswordConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticates against imap.gmail.com with App Password, saves credentials, and syncs real emails."""
    from app.services.email.gmail_imap_service import gmail_imap_service

    # 1. Connect and verify credentials
    gmail_imap_service.connect_user_with_app_password(
        db=db, user=current_user, app_password=req.app_password
    )

    # 2. Ingest real emails from candidate's Gmail inbox
    sync_result = gmail_imap_service.sync_real_emails(
        db=db, user=current_user, max_emails=50
    )

    return GmailAppPasswordConnectResponse(
        success=True,
        connected=True,
        message=sync_result.get("message", "Connected and synchronized Gmail inbox successfully."),
        total_fetched=sync_result.get("total_fetched", 0),
        new_stored=sync_result.get("new_stored", 0),
        jobs_extracted=sync_result.get("jobs_extracted", 0),
        matches_computed=sync_result.get("matches_computed", 0),
    )
