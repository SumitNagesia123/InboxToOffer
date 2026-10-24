from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    DashboardAnalyticsResponse,
    DashboardOverviewKPIs,
    SkillsGapResponse,
)
from app.services.analytics.analytics_service import analytics_service

router = APIRouter()


@router.get(
    "",
    response_model=DashboardAnalyticsResponse,
    summary="Get complete dashboard analytics",
    description="Returns high-level KPIs, pipeline stage distribution, work mode breakdown, platform sources, top in-demand skills, match score distribution, and recent activity timeline.",
)
def get_dashboard_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full dashboard analytics package for the authenticated user."""
    return analytics_service.get_dashboard_analytics(db=db, user=current_user)


@router.get(
    "/kpis",
    response_model=DashboardOverviewKPIs,
    summary="Get dashboard KPIs",
    description="Returns high-level intelligence metrics (emails ingested, jobs discovered, duplicates rate, average match score, active applications, conversion rates).",
)
def get_dashboard_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves high-level overview KPIs."""
    return analytics_service.get_dashboard_kpis(db=db, user=current_user)


@router.get(
    "/skills-gap",
    response_model=SkillsGapResponse,
    summary="Get skills gap and market demand analysis",
    description="Analyzes market skill requirements across discovered jobs and compares them with the candidate's active resume skills.",
)
def get_skills_gap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves skill demand vs candidate coverage analysis."""
    return analytics_service.get_skills_gap_analytics(db=db, user=current_user)
