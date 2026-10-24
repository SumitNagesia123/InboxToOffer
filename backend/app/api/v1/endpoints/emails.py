import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_current_user, get_db
from app.models.user import User
from app.schemas.email import (
    EmailDetailResponse,
    EmailListResponse,
    SyncRequest,
    SyncResponse,
    SweepPreviewItem,
    SweepRequest,
    SweepResponse,
    SweepSkippedItem,
)
from app.services.email.ingestion_service import email_ingestion_service

router = APIRouter()


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Trigger on-demand Gmail email synchronization",
    description="Fetches recent job-related emails from user's connected Gmail account, extracts text, cleans noise, and stores records.",
)
def sync_emails(
    req: Optional[SyncRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger manual Gmail synchronization for current user."""
    max_results = req.max_results if req else 50
    query_override = req.query_override if req else None

    return email_ingestion_service.sync_user_emails(
        db=db,
        user=current_user,
        max_results=max_results,
        query_override=query_override,
    )


@router.get(
    "",
    response_model=EmailListResponse,
    summary="List ingested emails",
    description="Returns a paginated list of ingested emails for the authenticated user with optional category and status filtering.",
)
def list_emails(
    pagination: Pagination = Depends(),
    category: Optional[str] = Query(None, description="Filter by email category (e.g. JOB, INTERVIEW, OFFER)"),
    status: Optional[str] = Query(None, description="Filter by processed status (e.g. PENDING, PROCESSED)"),
    search: Optional[str] = Query(None, description="Search keyword in subject or sender"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List emails belonging to authenticated user."""
    return email_ingestion_service.list_user_emails(
        db=db,
        user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        category=category,
        status=status,
        search=search,
    )


@router.get(
    "/{email_id}",
    response_model=EmailDetailResponse,
    summary="Get email details",
    description="Retrieves complete email details including cleaned body text and original HTML.",
)
def get_email(
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed email by ID."""
    return email_ingestion_service.get_user_email(
        db=db,
        user=current_user,
        email_id=email_id,
    )


@router.post(
    "/{email_id}/classify",
    response_model=EmailDetailResponse,
    summary="Classify email",
    description="Runs NLP classification on the specified email and updates category, confidence, and explanation.",
)
def classify_email(
    email_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run NLP classification on a specific email."""
    from app.services.email.classification_service import email_classification_service
    email = email_classification_service.classify_and_update_email(
        db=db,
        user=current_user,
        email_id=email_id,
    )
    return EmailDetailResponse.model_validate(email)


@router.post(
    "/classify-all",
    summary="Batch classify pending emails",
    description="Runs NLP classification across all pending ingested emails for current user.",
)
def classify_all_emails(
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch classify pending emails."""
    from app.services.email.classification_service import email_classification_service
    return email_classification_service.classify_all_pending(
        db=db,
        user=current_user,
        limit=limit,
    )


@router.post(
    "/sweep-non-job",
    response_model=SweepResponse,
    summary="Audit and sweep non-job emails",
    description="Identifies or purges non-job emails (e.g. Amazon orders, financial spam, antivirus alerts). Never deletes emails linked to active applications.",
)
def sweep_non_job_emails(
    req: SweepRequest = SweepRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Two-phase audit & sweep:
    - dry_run=True: Returns preview list of discardable emails and any skipped emails.
    - dry_run=False: Backs up rows to JSON and deletes explicitly confirmed email IDs and their job scraps (preserving applications).
    """
    import json
    import os
    from datetime import datetime, timezone
    from sqlalchemy import select, func
    from app.models.email import Email
    from app.models.job import Job
    from app.models.application import Application
    from app.services.email.triage_classifier import classify_email_triage, TriageDecision

    all_emails = db.scalars(
        select(Email).where(Email.user_id == current_user.id).order_by(Email.received_at.desc())
    ).all()

    total_scanned = len(all_emails)
    total_keep = 0
    total_unsure = 0
    total_discardable = 0
    preview_discards = []
    skipped_items = []

    # Map email_id -> email object
    email_map = {em.id: em for em in all_emails}

    if req.dry_run or not req.email_ids:
        # Phase 1: Dry run audit
        for em in all_emails:
            triage_res = classify_email_triage(
                sender=em.sender,
                subject=em.subject,
                snippet=em.body_text[:500] if em.body_text else "",
            )

            if triage_res.decision == TriageDecision.KEEP:
                total_keep += 1
            elif triage_res.decision == TriageDecision.UNSURE:
                total_unsure += 1
            else:
                total_discardable += 1
                # Check if this email produced any jobs that have applications
                jobs = db.scalars(select(Job).where(Job.source_email_id == em.id)).all()
                has_apps = False
                for j in jobs:
                    app_count = db.scalar(select(func.count(Application.id)).where(Application.job_id == j.id)) or 0
                    if app_count > 0:
                        has_apps = True
                        break

                if has_apps:
                    skipped_items.append(
                        SweepSkippedItem(
                            id=em.id,
                            sender=em.sender,
                            subject=em.subject,
                            reason="Job extracted from this email is active in your Application pipeline. Skipped to protect your application history.",
                        )
                    )
                else:
                    preview_discards.append(
                        SweepPreviewItem(
                            id=em.id,
                            sender=em.sender,
                            subject=em.subject,
                            category=triage_res.category.value,
                            confidence=triage_res.confidence,
                            reason=triage_res.reason,
                            received_at=em.received_at,
                            has_applications=False,
                            job_count=len(jobs),
                        )
                    )

        return SweepResponse(
            dry_run=True,
            total_scanned=total_scanned,
            total_discardable=total_discardable,
            total_skipped=len(skipped_items),
            total_unsure=total_unsure,
            total_keep=total_keep,
            preview_discards=preview_discards,
            skipped_items=skipped_items,
            removed_count=0,
            backup_path=None,
            message=f"Dry run complete: Scanned {total_scanned} emails. Found {len(preview_discards)} safe-to-purge non-job emails, {len(skipped_items)} skipped due to pipeline applications, and {total_keep + total_unsure} preserved.",
        )

    # Phase 2: Execution with explicit confirmed IDs
    target_ids = set(req.email_ids)
    to_delete_emails = []
    skipped_execution = []

    for eid in target_ids:
        em = email_map.get(eid)
        if not em:
            continue

        # Double check cascade safety: Never delete if linked to an application
        jobs = db.scalars(select(Job).where(Job.source_email_id == em.id)).all()
        has_apps = False
        for j in jobs:
            app_count = db.scalar(select(func.count(Application.id)).where(Application.job_id == j.id)) or 0
            if app_count > 0:
                has_apps = True
                break

        if has_apps:
            skipped_execution.append(
                SweepSkippedItem(
                    id=em.id,
                    sender=em.sender,
                    subject=em.subject,
                    reason="Has active application in pipeline. Skipped.",
                )
            )
        else:
            to_delete_emails.append((em, jobs))

    # Backup before deletion
    backup_path = None
    if to_delete_emails:
        backup_dir = os.path.join(os.getcwd(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"email_sweep_{timestamp_str}.json")

        backup_payload = [
            {
                "email_id": str(em.id),
                "gmail_message_id": em.gmail_message_id,
                "sender": em.sender,
                "recipient": em.recipient,
                "subject": em.subject,
                "received_at": em.received_at.isoformat(),
                "category": em.category,
                "body_text": em.body_text,
                "jobs": [
                    {"id": str(j.id), "title": j.title, "company_name": j.company_name}
                    for j in jobs
                ],
            }
            for em, jobs in to_delete_emails
        ]

        with open(backup_path, "w", encoding="utf-8") as bf:
            json.dump(backup_payload, bf, indent=2)

    # Execute atomic deletion
    removed_count = 0
    for em, jobs in to_delete_emails:
        for j in jobs:
            db.delete(j)
        db.delete(em)
        removed_count += 1

    db.commit()

    return SweepResponse(
        dry_run=False,
        total_scanned=total_scanned,
        total_discardable=len(target_ids),
        total_skipped=len(skipped_execution),
        total_unsure=0,
        total_keep=total_scanned - removed_count,
        preview_discards=[],
        skipped_items=skipped_execution,
        removed_count=removed_count,
        backup_path=backup_path,
        message=f"Sweep execution complete: Permanently purged {removed_count} non-job emails (backed up to {backup_path}). Skipped {len(skipped_execution)}.",
    )

