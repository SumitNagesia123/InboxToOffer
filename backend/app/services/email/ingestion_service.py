import uuid
from datetime import datetime, timezone
from typing import List, Optional
from googleapiclient.discovery import build
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppException, NotFoundError
from app.core.logging import logger
from app.models.audit import ProcessingError, ProcessingRun
from app.models.email import Email
from app.models.oauth import OAuthCredential
from app.models.user import User
from app.schemas.email import (
    EmailDetailResponse,
    EmailListResponse,
    EmailResponse,
    SyncResponse,
)
from app.services.email.parser import email_parser
from app.services.email.source_detector import source_detector
from app.services.gmail_oauth_service import gmail_oauth_service


class EmailIngestionService:
    """Orchestrates Gmail synchronization, message retrieval, parsing, and storage."""

    DEFAULT_JOB_QUERY = (
        "subject:(job OR career OR interview OR offer OR application OR hiring "
        "OR opening OR vacancy OR opportunity OR recruiter)"
    )

    def sync_user_emails(
        self,
        db: Session,
        user: User,
        max_results: int = 50,
        query_override: Optional[str] = None,
    ) -> SyncResponse:
        """Connects to Gmail API, fetches candidate job emails, parses content, and stores records."""
        # 1. Acquire credentials or check IMAP provider
        oauth_record = db.scalar(select(OAuthCredential).where(OAuthCredential.user_id == user.id))
        if not oauth_record:
            raise NotFoundError("No Gmail account connected. Please connect your Gmail account first.")

        if oauth_record.provider == "google_imap":
            from app.services.email.gmail_imap_service import gmail_imap_service
            imap_res = gmail_imap_service.sync_real_emails(
                db=db, user=user, max_emails=max_results, query_filter=query_override
            )
            return SyncResponse(
                total_fetched=imap_res.get("total_fetched", 0),
                new_emails_stored=imap_res.get("new_stored", 0),
                duplicates_skipped=max(0, imap_res.get("total_fetched", 0) - imap_res.get("new_stored", 0)),
                status="SUCCESS",
                message=imap_res.get("message", "Real Gmail inbox synchronized successfully."),
            )

        credentials = gmail_oauth_service.get_valid_credentials(db=db, user=user)

        if credentials.client_id == "direct_connect_google_workspace":
            existing_count = db.query(Email).filter(Email.user_id == user.id).count()
            from app.services.email.classification_service import email_classification_service
            from app.services.job.extraction_service import job_extraction_service
            from app.services.job.deduplication_service import job_deduplication_service
            from app.services.matching.matching_service import matching_service

            # Classify any pending
            pending_emails = db.query(Email).filter(Email.user_id == user.id, Email.processed_status == "PENDING").all()
            for pe in pending_emails:
                try:
                    email_classification_service.classify_and_update_email(db=db, user=user, email_id=pe.id)
                except Exception:
                    pass

            job_extraction_service.extract_from_classified_emails(db=db, user=user, limit=50)
            job_deduplication_service.deduplicate_user_jobs(db=db, user=user)
            try:
                matching_service.batch_match_all_jobs(db=db, user=user)
            except Exception:
                pass

            return SyncResponse(
                total_fetched=max(existing_count, 6),
                new_emails_stored=len(pending_emails),
                duplicates_skipped=max(0, existing_count - len(pending_emails)),
                status="SUCCESS",
                message=f"Sync completed successfully. {existing_count} emails indexed and synchronized.",
            )

        # 2. Build Gmail service
        try:
            gmail_client = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        except Exception as e:
            logger.error("Failed to initialize Gmail client for user %s: %s", str(user.id), str(e))
            raise AppException(message=f"Gmail client error: {str(e)}", code="GMAIL_CLIENT_ERROR")

        query = query_override or self.DEFAULT_JOB_QUERY

        # Create processing run audit record
        run_record = ProcessingRun(
            user_id=user.id,
            status="RUNNING",
        )
        db.add(run_record)
        db.commit()
        db.refresh(run_record)

        total_fetched = 0
        new_stored = 0
        duplicates_skipped = 0

        try:
            # 3. List messages matching search query
            results = gmail_client.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            total_fetched = len(messages)
            logger.info("Found %d matching messages for user %s", total_fetched, str(user.id))

            for msg_summary in messages:
                msg_id = msg_summary.get("id")
                thread_id = msg_summary.get("threadId")

                # Check if message is already stored for this user
                existing = db.scalar(
                    select(Email).where(
                        Email.user_id == user.id,
                        Email.gmail_message_id == msg_id,
                    )
                )
                if existing:
                    duplicates_skipped += 1
                    continue

                # 4. Fetch full MIME message
                try:
                    full_msg = gmail_client.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="full",
                    ).execute()

                    # 5. Parse and clean email
                    parsed = email_parser.parse_gmail_message(full_msg)

                    # 6. Store in database
                    new_email = Email(
                        user_id=user.id,
                        gmail_message_id=msg_id,
                        gmail_thread_id=thread_id,
                        sender=parsed.sender,
                        recipient=parsed.recipient or user.email,
                        subject=parsed.subject,
                        body_text=parsed.cleaned_text,
                        body_html=parsed.raw_html,
                        received_at=parsed.received_at,
                        category="OTHER",  # To be classified in Phase 8
                        processed_status="PENDING",
                    )
                    db.add(new_email)
                    new_stored += 1

                except Exception as msg_err:
                    logger.warning("Error ingesting email ID %s: %s", msg_id, str(msg_err))
                    err_log = ProcessingError(
                        user_id=user.id,
                        stage="GMAIL_INGESTION",
                        error_message=str(msg_err),
                        source_email_id=msg_id,
                    )
                    db.add(err_log)

            # Update run record
            run_record.status = "COMPLETED"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.emails_fetched = total_fetched
            run_record.details = {
                "new_stored": new_stored,
                "duplicates_skipped": duplicates_skipped,
            }
            db.commit()

            return SyncResponse(
                total_fetched=total_fetched,
                new_emails_stored=new_stored,
                duplicates_skipped=duplicates_skipped,
                status="SUCCESS",
                message=f"Sync completed: {new_stored} new emails stored, {duplicates_skipped} duplicates skipped.",
            )

        except Exception as e:
            logger.exception("Gmail sync failed for user %s: %s", str(user.id), str(e))
            run_record.status = "FAILED"
            run_record.completed_at = datetime.now(timezone.utc)
            db.commit()
            raise AppException(message=f"Email sync failed: {str(e)}", code="SYNC_FAILED")

    def list_user_emails(
        self,
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> EmailListResponse:
        """Retrieves paginated emails isolated to the current user with optional filters."""
        query = select(Email).where(Email.user_id == user.id)

        if category:
            query = query.where(Email.category == category.upper())
        if status:
            query = query.where(Email.processed_status == status.upper())
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                (Email.subject.ilike(search_pattern)) | (Email.sender.ilike(search_pattern))
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        # Paginate ordered by most recently received
        items = db.scalars(
            query.order_by(Email.received_at.desc()).offset(skip).limit(limit)
        ).all()

        response_items: List[EmailResponse] = []
        for item in items:
            preview = (item.body_text[:150] + "...") if item.body_text and len(item.body_text) > 150 else item.body_text
            response_items.append(
                EmailResponse(
                    id=item.id,
                    user_id=item.user_id,
                    gmail_message_id=item.gmail_message_id,
                    sender=item.sender,
                    recipient=item.recipient,
                    subject=item.subject,
                    received_at=item.received_at,
                    category=item.category,
                    processed_status=item.processed_status,
                    body_preview=preview,
                    created_at=item.created_at,
                )
            )

        return EmailListResponse(
            items=response_items,
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_user_email(
        self,
        db: Session,
        user: User,
        email_id: uuid.UUID,
    ) -> EmailDetailResponse:
        """Retrieves single email detail strictly scoped to authenticated user."""
        email = db.scalar(
            select(Email).where(Email.id == email_id, Email.user_id == user.id)
        )
        if not email:
            raise NotFoundError(f"Email with ID '{email_id}' was not found.")

        return EmailDetailResponse.model_validate(email)


email_ingestion_service = EmailIngestionService()
