from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    applications,
    auth,
    digest,
    emails,
    gmail,
    health,
    jobs,
    matches,
    notifications,
    resumes,
    settings,
)

api_router = APIRouter()

# Core System Routes
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(gmail.router, prefix="/gmail", tags=["Gmail"])
api_router.include_router(emails.router, prefix="/emails", tags=["Emails"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(matches.router, prefix="/matches", tags=["Matches"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(digest.router, prefix="/digest", tags=["Digest"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
