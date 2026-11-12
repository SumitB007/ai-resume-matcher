"""Analytics endpoints — track resume score improvements, skill gap trends, and dashboard statistics."""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    ResumeProgressResponse,
    ResumeEvaluationsSummaryResponse,
    UserAnalyticsDashboardResponse,
)
from app.services.analytics_service import (
    get_resume_progress_for_job,
    get_resume_evaluations_summary,
    get_user_analytics_dashboard,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/resume-progress/{job_id}",
    response_model=ResumeProgressResponse,
    summary="Track score improvements across multiple resume versions for a specific job",
)
async def resume_version_progress(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze score improvements and acquired skills across resume iterations for the same job description.

    Directly computes:
    - Initial vs latest match score
    - Net score improvement percentage
    - Average match score
    - Skills gained (gaps present in early iterations that were resolved)
    - Chronological evaluation timeline
    """
    return await get_resume_progress_for_job(
        job_id=job_id,
        user_id=current_user.id,
        db=db,
    )


@router.get(
    "/resumes/{resume_id}/progress",
    response_model=ResumeEvaluationsSummaryResponse,
    summary="Get performance overview of a resume across all evaluated jobs",
)
async def resume_evaluations_summary(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Summarize match scores, highest/lowest scores, and evaluated jobs for a specific resume."""
    return await get_resume_evaluations_summary(
        resume_id=resume_id,
        user_id=current_user.id,
        db=db,
    )


@router.get(
    "/dashboard",
    response_model=UserAnalyticsDashboardResponse,
    summary="Comprehensive ATS user analytics dashboard",
)
async def analytics_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate overall ATS dashboard metrics for the authenticated user.

    Includes:
    - Counts of resumes, jobs, and matches
    - Average, highest, and lowest match scores
    - Top missing skills across all job applications (gap analysis trends)
    - Top candidate skills present in user resumes
    - Recent matches timeline
    """
    return await get_user_analytics_dashboard(
        user_id=current_user.id,
        db=db,
    )
