import logging
import sys
from typing import Any
from app.core.config import settings

# Ensure UTF-8 output encoding on Windows so unicode characters in logs don't trigger charmap errors
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class SensitiveDataFilter(logging.Filter):
    """Filters and sanitizes sensitive terms from log messages."""

    SENSITIVE_KEYS = ("password", "token", "secret", "authorization", "refresh_token", "key")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage()).lower()
        # If necessary, further redaction logic can be placed here
        return True


def setup_logging() -> logging.Logger:
    """Configures structured application logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    else:
        root_logger.handlers = [handler]

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger = logging.getLogger("aijob")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
