import base64
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from bs4 import BeautifulSoup


class ParsedEmail:
    """Holds parsed and cleaned email content."""

    def __init__(
        self,
        message_id: str,
        sender: str,
        recipient: str,
        subject: str,
        received_at: datetime,
        raw_html: Optional[str] = None,
        cleaned_text: str = "",
        links: Optional[List[str]] = None,
    ):
        self.message_id = message_id
        self.sender = sender
        self.recipient = recipient
        self.subject = subject
        self.received_at = received_at
        self.raw_html = raw_html
        self.cleaned_text = cleaned_text
        self.links = links or []


class EmailParser:
    """MIME and HTML parsing, tracking link normalization, and text cleaning."""

    # Query params to strip from tracking URLs
    TRACKING_PARAMS = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "ref",
        "trk",
        "tracking_id",
        "mc_cid",
        "mc_eid",
        "midToken",
        "trkEmail",
    }

    # Boilerplate patterns to remove from email text
    UNSUBSCRIBE_PATTERNS = [
        r"(?i)you\s+are\s+receiving\s+this\s+email\s+because.*",
        r"(?i)to\s+unsubscribe\s+(from|click|please).*",
        r"(?i)click\s+here\s+to\s+unsubscribe.*",
        r"(?i)unsubscribe\s*\|\s*update\s+preferences.*",
        r"(?i)manage\s+your\s+email\s+preferences.*",
        r"(?i)privacy\s+policy\s*\|\s*terms\s+of\s+service.*",
        r"(?i)©\s*\d{4}\s+.*all\s+rights\s+reserved\b.*",
    ]

    @staticmethod
    def decode_base64_payload(data: str) -> str:
        """Decodes URL-safe base64 MIME payload."""
        if not data:
            return ""
        try:
            # Handle padding if missing
            padding = len(data) % 4
            if padding:
                data += "=" * (4 - padding)
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""

    @classmethod
    def clean_url(cls, url: str) -> str:
        """Strips marketing and tracking query parameters from URLs."""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            query_dict = parse_qs(parsed.query, keep_blank_values=False)
            filtered_query = {
                k: v for k, v in query_dict.items() if k.lower() not in cls.TRACKING_PARAMS
            }
            new_query = urlencode(filtered_query, doseq=True)
            cleaned = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            ))
            return cleaned.rstrip("?")
        except Exception:
            return url

    @classmethod
    def clean_html(cls, html_content: str) -> Tuple[str, List[str]]:
        """Cleans HTML content, extracts text, removes noise, and extracts links."""
        if not html_content:
            return "", []

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove dangerous or non-content tags
        for tag in soup(["script", "style", "head", "noscript", "svg", "iframe", "footer", "header", "nav"]):
            tag.decompose()

        # 2. Extract links and clean tracking params
        extracted_links: List[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if href.startswith("http://") or href.startswith("https://"):
                cleaned = cls.clean_url(href)
                extracted_links.append(cleaned)
                link_text = a_tag.get_text().strip()
                if link_text and link_text.lower() not in ("unsubscribe", "view in browser", "privacy"):
                    a_tag.replace_with(f" {link_text} ")
                else:
                    a_tag.decompose()

        # 3. Get text content
        raw_text = soup.get_text(separator="\n")

        # 4. Clean boilerplate and unsubscribe lines
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        cleaned_lines = []
        for line in lines:
            # Check unsubscribe boilerplate
            if any(re.search(pat, line) for pat in cls.UNSUBSCRIBE_PATTERNS):
                continue
            cleaned_lines.append(line)

        # 5. Collapse excessive whitespace
        text_result = "\n".join(cleaned_lines)
        text_result = re.sub(r"\n{3,}", "\n\n", text_result).strip()

        # Deduplicate links preserving order
        seen_links = set()
        unique_links = []
        for link in extracted_links:
            if link not in seen_links:
                seen_links.add(link)
                unique_links.append(link)

        return text_result, unique_links

    @classmethod
    def extract_mime_parts(cls, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Recursively traverses MIME parts to extract plain-text and HTML bodies."""
        html_body: Optional[str] = None
        plain_body: Optional[str] = None

        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")

        if body_data:
            decoded = cls.decode_base64_payload(body_data)
            if "text/html" in mime_type:
                html_body = decoded
            elif "text/plain" in mime_type:
                plain_body = decoded

        parts = payload.get("parts", [])
        for part in parts:
            part_html, part_plain = cls.extract_mime_parts(part)
            if part_html and not html_body:
                html_body = part_html
            if part_plain and not plain_body:
                plain_body = part_plain

        return html_body, plain_body

    @classmethod
    def parse_gmail_message(cls, message_payload: Dict[str, Any]) -> ParsedEmail:
        """Parses a full Gmail API message object into structured ParsedEmail."""
        msg_id = message_payload.get("id", "")
        headers = message_payload.get("payload", {}).get("headers", [])

        header_dict: Dict[str, str] = {}
        for h in headers:
            header_dict[h.get("name", "").lower()] = h.get("value", "")

        subject = header_dict.get("subject", "No Subject")
        sender = header_dict.get("from", "Unknown Sender")
        recipient = header_dict.get("to", "")
        date_str = header_dict.get("date", "")

        # Parse date
        received_at: datetime
        if date_str:
            try:
                received_at = parsedate_to_datetime(date_str)
                if received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
            except Exception:
                received_at = datetime.now(timezone.utc)
        else:
            internal_date_ms = message_payload.get("internalDate")
            if internal_date_ms:
                try:
                    received_at = datetime.fromtimestamp(int(internal_date_ms) / 1000.0, tz=timezone.utc)
                except Exception:
                    received_at = datetime.now(timezone.utc)
            else:
                received_at = datetime.now(timezone.utc)

        # Extract MIME bodies
        raw_html, plain_text = cls.extract_mime_parts(message_payload.get("payload", {}))

        # Clean text
        if raw_html:
            cleaned_text, links = cls.clean_html(raw_html)
        elif plain_text:
            cleaned_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()
            # Extract links from plaintext
            found_urls = re.findall(r"https?://[^\s<>\"']+", plain_text)
            links = [cls.clean_url(u) for u in found_urls]
        else:
            # Fallback snippet
            cleaned_text = message_payload.get("snippet", "")
            links = []

        return ParsedEmail(
            message_id=msg_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            received_at=received_at,
            raw_html=raw_html,
            cleaned_text=cleaned_text,
            links=links,
        )


email_parser = EmailParser()
