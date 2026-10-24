import os
import re
import uuid
from pathlib import Path
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import logger
from app.models.resume import Resume, ResumeSkill
from app.models.skill import Skill
from app.models.user import User
from app.schemas.resume import (
    ContactInfo,
    EducationItem,
    ParsedResumeData,
    ResumeResponse,
    ResumeTextResponse,
    ResumeUploadResponse,
    SkillItem,
    StructuredResumeResponse,
    WorkExperienceItem,
)
from app.services.resume.extractor import ExtractedResumeText, resume_extractor
from app.services.resume.parser import resume_parser


class ResumeService:
    """Handles candidate resume upload, text extraction, local persistence, and DB lifecycle."""

    def _get_storage_directory(self, user_id: uuid.UUID) -> Path:
        """Resolves and creates user-specific upload directory on disk."""
        target_dir = Path(settings.UPLOAD_DIR) / "resumes" / str(user_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir

    def _sanitize_filename(self, filename: str) -> str:
        """Replaces hazardous characters with safe underscores."""
        clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename.strip())
        return clean or "resume.pdf"

    def _save_file_to_disk(self, user_id: uuid.UUID, filename: str, file_bytes: bytes) -> str:
        """Stores binary resume on disk and returns the relative path string."""
        storage_dir = self._get_storage_directory(user_id)
        safe_name = self._sanitize_filename(filename)
        # Prefix with uuid chunk to guarantee uniqueness across uploads
        unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        destination = storage_dir / unique_name

        with open(destination, "wb") as f:
            f.write(file_bytes)

        return str(destination)

    def _get_or_create_skill(self, db: Session, name: str, category: Optional[str] = "Technical") -> Skill:
        """Finds or creates Skill taxonomy record."""
        norm_name = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
        skill = db.scalar(select(Skill).where(Skill.normalized_name == norm_name))
        if not skill:
            skill = Skill(
                name=name,
                normalized_name=norm_name,
                category=category,
            )
            db.add(skill)
            db.flush()
        return skill

    def upload_and_process_resume(
        self,
        db: Session,
        user: User,
        filename: str,
        file_bytes: bytes,
    ) -> Tuple[Resume, ResumeUploadResponse]:
        """Validates, extracts text from, and stores candidate resume."""
        # 1. Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        file_size = len(file_bytes)
        if file_size == 0:
            raise ValidationError("The uploaded file is empty.")
        if file_size > max_bytes:
            raise ValidationError(
                f"File size ({file_size / (1024*1024):.1f}MB) exceeds the maximum permitted limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        # 2. Extract and clean text content
        extracted: ExtractedResumeText = resume_extractor.extract(
            filename=filename,
            file_bytes=file_bytes,
        )

        # 3. Save physical file to disk
        file_path = self._save_file_to_disk(
            user_id=user.id,
            filename=filename,
            file_bytes=file_bytes,
        )

        # 4. Check for existing active resume (resumes.user_id is UNIQUE)
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))

        if resume:
            # Clean up old file if present
            try:
                old_path = Path(resume.file_path)
                if old_path.exists() and old_path.is_file():
                    old_path.unlink()
            except Exception as e:
                logger.warning("Could not delete prior resume file '%s': %s", resume.file_path, str(e))

            # Update existing record
            resume.file_name = filename
            resume.file_path = file_path
            resume.extracted_text = extracted.clean_text
            resume.parsed_summary = extracted.text_preview
        else:
            # Create new record
            resume = Resume(
                user_id=user.id,
                file_name=filename,
                file_path=file_path,
                extracted_text=extracted.clean_text,
                parsed_summary=extracted.text_preview,
            )
            db.add(resume)

        db.commit()
        db.refresh(resume)

        # Automatically parse and populate structured skills and experience
        try:
            self.parse_and_persist_resume(db=db, user=user)
        except Exception as e:
            logger.warning("Auto-parsing resume on upload encountered error: %s", str(e))

        response_meta = ResumeUploadResponse(
            id=resume.id,
            user_id=resume.user_id,
            file_name=resume.file_name,
            file_size_bytes=file_size,
            character_count=extracted.character_count,
            word_count=extracted.word_count,
            page_count=extracted.page_count,
            text_preview=extracted.text_preview,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )

        logger.info(
            "Processed resume '%s' for user %s: %d characters, %d words across %d page(s).",
            filename, str(user.id), extracted.character_count, extracted.word_count, extracted.page_count,
        )
        return resume, response_meta

    def parse_and_persist_resume(self, db: Session, user: User) -> StructuredResumeResponse:
        """Parses active candidate resume into structured fields and links skills in the database."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise NotFoundError("No resume found for current user to parse.")

        # Execute parsing engine
        parsed: ParsedResumeData = resume_parser.parse(resume.extracted_text)

        # Update Resume entity
        if parsed.summary:
            resume.parsed_summary = parsed.summary
        if parsed.total_experience_years is not None:
            resume.total_experience_years = parsed.total_experience_years

        if parsed.education:
            resume.education_summary = {
                "items": [edu.model_dump() for edu in parsed.education]
            }

        # Clear and repopulate resume_skills
        db.query(ResumeSkill).filter(ResumeSkill.resume_id == resume.id).delete()

        for skill_item in parsed.skills:
            skill_obj = self._get_or_create_skill(db, skill_item.name, skill_item.category)
            resume_skill = ResumeSkill(
                resume_id=resume.id,
                skill_id=skill_obj.id,
                years_experience=skill_item.years_experience,
            )
            db.add(resume_skill)

        db.commit()
        db.refresh(resume)

        return StructuredResumeResponse(
            id=resume.id,
            user_id=resume.user_id,
            file_name=resume.file_name,
            parsed_data=parsed,
            skills_count=len(parsed.skills),
            experience_count=len(parsed.experience),
            education_count=len(parsed.education),
            total_experience_years=resume.total_experience_years,
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )

    def get_resume(self, db: Session, user: User) -> ResumeResponse:
        """Retrieves active resume for authenticated user."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise NotFoundError("No resume uploaded yet for current user.")

        words = resume.extracted_text.split()
        return ResumeResponse(
            id=resume.id,
            user_id=resume.user_id,
            file_name=resume.file_name,
            extracted_text=resume.extracted_text,
            parsed_summary=resume.parsed_summary,
            total_experience_years=resume.total_experience_years,
            education_summary=resume.education_summary,
            character_count=len(resume.extracted_text),
            word_count=len(words),
            created_at=resume.created_at,
            updated_at=resume.updated_at,
        )

    def get_structured_resume(self, db: Session, user: User) -> StructuredResumeResponse:
        """Retrieves or parses structured profile for active user resume."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise NotFoundError("No resume found for current user.")

        # Re-parse or retrieve existing structured representation
        return self.parse_and_persist_resume(db=db, user=user)

    def get_resume_text(self, db: Session, user: User) -> ResumeTextResponse:
        """Retrieves clean extracted plain text for active resume."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise NotFoundError("No resume uploaded yet for current user.")

        words = resume.extracted_text.split()
        return ResumeTextResponse(
            file_name=resume.file_name,
            character_count=len(resume.extracted_text),
            word_count=len(words),
            extracted_text=resume.extracted_text,
        )

    def delete_resume(self, db: Session, user: User) -> None:
        """Deletes user's active resume record and removes file from disk."""
        resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
        if not resume:
            raise NotFoundError("No resume found to delete.")

        # Remove physical file
        try:
            path = Path(resume.file_path)
            if path.exists() and path.is_file():
                path.unlink()
        except Exception as e:
            logger.warning("Could not delete resume file on disk '%s': %s", resume.file_path, str(e))

        db.delete(resume)
        db.commit()
        logger.info("Successfully deleted resume for user %s", str(user.id))


resume_service = ResumeService()
