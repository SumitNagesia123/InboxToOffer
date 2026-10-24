import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.email import Email
from app.models.user import User
from app.schemas.nlp import BatchClassifyResponse, EmailClassificationResult
from app.services.nlp.classifier import email_classifier


class EmailClassificationService:
    """Service orchestrating email NLP categorization and database synchronization."""

    def classify_and_update_email(self, db: Session, user: User, email_id: uuid.UUID) -> Email:
        """Classifies a single email and persists the resulting category and explanation."""
        email = db.scalar(
            select(Email).where(Email.id == email_id, Email.user_id == user.id)
        )
        if not email:
            raise NotFoundError(f"Email with ID '{email_id}' was not found.")

        result = email_classifier.classify(
            subject=email.subject,
            sender=email.sender,
            body=email.body_text or "",
        )

        email.category = result.category.value
        email.classification_confidence = result.confidence
        email.classification_reason = result.reason
        email.processed_status = "CLASSIFIED"

        db.commit()
        db.refresh(email)
        logger.info(
            "Classified email %s as %s with confidence %.2f",
            str(email.id),
            email.category,
            email.classification_confidence,
        )
        return email

    def classify_all_pending(self, db: Session, user: User, limit: int = 50) -> BatchClassifyResponse:
        """Processes all pending emails for a user and applies NLP classification."""
        pending_emails = db.scalars(
            select(Email)
            .where(Email.user_id == user.id, Email.processed_status == "PENDING")
            .limit(limit)
        ).all()

        classified_count = 0
        failed_count = 0

        for email in pending_emails:
            try:
                result = email_classifier.classify(
                    subject=email.subject,
                    sender=email.sender,
                    body=email.body_text or "",
                )
                email.category = result.category.value
                email.classification_confidence = result.confidence
                email.classification_reason = result.reason
                email.processed_status = "CLASSIFIED"
                classified_count += 1
            except Exception as e:
                logger.error("Failed to classify email %s: %s", str(email.id), str(e))
                failed_count += 1

        db.commit()
        return BatchClassifyResponse(
            total_processed=len(pending_emails),
            classified_count=classified_count,
            failed_count=failed_count,
            message=f"Batch classification complete: {classified_count} classified, {failed_count} failed.",
        )


email_classification_service = EmailClassificationService()
