import io
import re
from dataclasses import dataclass
from typing import Optional
import pypdf

from app.core.errors import ValidationError
from app.core.logging import logger


@dataclass
class ExtractedResumeText:
    clean_text: str
    character_count: int
    word_count: int
    page_count: int
    text_preview: str


class ResumeTextExtractor:
    """Extracts, cleans, and normalizes candidate resume text from PDFs and text files."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """Sanitizes text by eliminating null bytes, control codes, and consolidating whitespace."""
        if not raw_text:
            return ""

        # Remove null bytes and control characters (except newline \n and tab \t)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", raw_text)

        # Standardize line breaks
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse horizontal whitespace
        text = re.sub(r"[ \t]+", " ", text)

        # Remove trailing/leading spaces on lines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Collapse excessive newlines (max 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def extract_from_pdf(self, file_bytes: bytes) -> ExtractedResumeText:
        """Extracts text content across all pages of a PDF document using pypdf."""
        try:
            stream = io.BytesIO(file_bytes)
            reader = pypdf.PdfReader(stream)
            num_pages = len(reader.pages)
            if num_pages == 0:
                raise ValidationError("The uploaded PDF file contains no pages.")

            extracted_pages = []
            for idx, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    extracted_pages.append(page_text)
                except Exception as e:
                    logger.warning("Could not extract text from PDF page %d: %s", idx + 1, str(e))

            raw_combined = "\n\n".join(extracted_pages)
            clean_text = self.clean_text(raw_combined)

            if len(clean_text) < 15:
                raise ValidationError(
                    "Extracted resume text is empty or too short. Ensure the PDF is not an image-only scan."
                )

            words = clean_text.split()
            preview = clean_text[:400] + ("..." if len(clean_text) > 400 else "")

            return ExtractedResumeText(
                clean_text=clean_text,
                character_count=len(clean_text),
                word_count=len(words),
                page_count=num_pages,
                text_preview=preview,
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to parse PDF document: %s", str(e))
            raise ValidationError(f"Invalid or corrupted PDF file: {str(e)}")

    def extract_from_plain_text(self, file_bytes: bytes) -> ExtractedResumeText:
        """Extracts text from plain text or markdown resume documents."""
        try:
            try:
                raw_text = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raw_text = file_bytes.decode("latin-1", errors="replace")

            clean_text = self.clean_text(raw_text)
            if len(clean_text) < 15:
                raise ValidationError("Uploaded text resume contains insufficient content (minimum 15 characters required).")

            words = clean_text.split()
            preview = clean_text[:400] + ("..." if len(clean_text) > 400 else "")

            return ExtractedResumeText(
                clean_text=clean_text,
                character_count=len(clean_text),
                word_count=len(words),
                page_count=1,
                text_preview=preview,
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Failed to parse text document: %s", str(e))
            raise ValidationError(f"Unable to read text file: {str(e)}")

    def extract(self, filename: str, file_bytes: bytes) -> ExtractedResumeText:
        """Determines extractor strategy by file extension and executes extraction."""
        lower_name = filename.lower()
        if lower_name.endswith(".pdf"):
            return self.extract_from_pdf(file_bytes)
        elif any(lower_name.endswith(ext) for ext in [".txt", ".text", ".md", ".markdown"]):
            return self.extract_from_plain_text(file_bytes)
        else:
            raise ValidationError(
                f"Unsupported resume file format '{filename}'. Allowed formats: PDF (.pdf), Text (.txt), Markdown (.md)."
            )


resume_extractor = ResumeTextExtractor()
