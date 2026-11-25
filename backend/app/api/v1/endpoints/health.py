from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


def _run_health_check(db: Session):
    db_status = "disconnected"
    is_healthy = False

    try:
        # Ping the database
        db.execute(text("SELECT 1"))
        db_status = "connected"
        is_healthy = True
    except Exception as e:
        logger.error("Health check failed database connectivity test: %s", str(e))
        db_status = "error"

    payload = {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": db_status,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if is_healthy:
        return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
    else:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)


@router.get(
    "/health",
    summary="Health Check",
    description="Check the operational health of the backend API and database connectivity.",
    tags=["Health"],
)
@router.get("/health/")
@router.head("/health")
@router.head("/health/")
@router.post("/health")
@router.post("/health/")
def health_check(db: Session = Depends(get_db)):
    """Verifies API status and database connectivity."""
    return _run_health_check(db)
