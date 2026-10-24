import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EmailResponse(BaseModel):
    """Summarized email record for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    gmail_message_id: str
    sender: str
    recipient: str
    subject: str
    received_at: datetime
    category: str
    processed_status: str
    body_preview: Optional[str] = None
    created_at: datetime


class EmailDetailResponse(BaseModel):
    """Comprehensive email details including full cleaned text and original HTML."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    sender: str
    recipient: str
    subject: str
    received_at: datetime
    category: str
    classification_confidence: Optional[float] = None
    classification_reason: Optional[str] = None
    processed_status: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    created_at: datetime


class EmailListResponse(BaseModel):
    """Paginated list of emails."""
    items: List[EmailResponse]
    total: int
    skip: int
    limit: int


class SyncRequest(BaseModel):
    """Optional parameters for manual Gmail synchronization."""
    max_results: int = Field(50, ge=1, le=200, description="Max emails to fetch in this batch")
    query_override: Optional[str] = Field(None, description="Custom Gmail search query filter")


class SyncResponse(BaseModel):
    """Result summary of Gmail sync operation."""
    total_fetched: int
    new_emails_stored: int
    duplicates_skipped: int
    status: str
    message: str


class SweepPreviewItem(BaseModel):
    id: uuid.UUID
    sender: str
    subject: str
    category: str
    confidence: float
    reason: str
    received_at: datetime
    has_applications: bool = False
    job_count: int = 0


class SweepSkippedItem(BaseModel):
    id: uuid.UUID
    sender: str
    subject: str
    reason: str


class SweepRequest(BaseModel):
    dry_run: bool = Field(True, description="When true, only returns what would be removed without deleting")
    email_ids: Optional[List[uuid.UUID]] = Field(None, description="Explicit list of email IDs to delete when dry_run=False")


class SweepResponse(BaseModel):
    dry_run: bool
    total_scanned: int
    total_discardable: int
    total_skipped: int
    total_unsure: int
    total_keep: int
    preview_discards: List[SweepPreviewItem] = []
    skipped_items: List[SweepSkippedItem] = []
    removed_count: int = 0
    backup_path: Optional[str] = None
    message: str

