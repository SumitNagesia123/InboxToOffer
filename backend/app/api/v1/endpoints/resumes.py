from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import ValidationError
from app.models.user import User
from app.schemas.resume import (
    ResumeResponse,
    ResumeTextResponse,
    ResumeUploadResponse,
    StructuredResumeResponse,
)
from app.services.resume.resume_service import resume_service

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".text", ".markdown"}


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and extract resume",
    description="Accepts a PDF, Markdown, or Text resume file, extracts and cleans its text, and stores it for matching.",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF, TXT, or MD)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Uploads resume, validates format, extracts text, and stores resume entity."""
    filename = file.filename or "resume.pdf"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file format '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    file_bytes = await file.read()
    _, response_meta = resume_service.upload_and_process_resume(
        db=db,
        user=current_user,
        filename=filename,
        file_bytes=file_bytes,
    )
    return response_meta


@router.post(
    "/parse",
    response_model=StructuredResumeResponse,
    summary="Parse candidate resume into structured profile",
    description="Extracts contact details, experience chronology, education degrees, and skills taxonomy.",
)
def parse_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Triggers structuring engine on user's active uploaded resume."""
    return resume_service.parse_and_persist_resume(db=db, user=current_user)


@router.get(
    "/me",
    response_model=ResumeResponse,
    summary="Get active user resume",
    description="Retrieves the authenticated user's current uploaded resume and extracted details.",
)
def get_my_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves metadata and structured details of user's active resume."""
    return resume_service.get_resume(db=db, user=current_user)


@router.get(
    "/me/structured",
    response_model=StructuredResumeResponse,
    summary="Get structured resume profile",
    description="Returns the full parsed breakdown including skills, experience items, and degrees.",
)
def get_my_structured_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full structured profile for active resume."""
    return resume_service.get_structured_resume(db=db, user=current_user)


@router.get(
    "/me/text",
    response_model=ResumeTextResponse,
    summary="Get raw extracted resume text",
    description="Returns the clean, normalized plain text extracted from the user's active resume.",
)
def get_my_resume_text(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns extracted plain text for candidate profile."""
    return resume_service.get_resume_text(db=db, user=current_user)


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Delete active resume",
    description="Removes the user's resume file from disk and deletes the database record.",
)
def delete_my_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes active resume record and underlying file."""
    resume_service.delete_resume(db=db, user=current_user)
    return {"message": "Resume successfully deleted."}
