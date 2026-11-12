"""Analytics service — computes resume score progression, gap trends, and dashboard metrics.

Tracks score improvements across resume iterations for target jobs,
identifies persistent skill gaps, and summarizes candidate match performance.
"""

from collections import Counter
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.schemas.analytics import (
    TimelineMatchEntry,
    ResumeProgressResponse,
    ResumeJobEvaluationEntry,
    ResumeEvaluationsSummaryResponse,
    SkillFrequency,
    UserAnalyticsDashboardResponse,
)

logger = logging.getLogger(__name__)


async def get_resume_progress_for_job(
    job_id: int,
    user_id: int,
    db: AsyncSession,
) -> ResumeProgressResponse:
    """Calculate score improvements and skill acquisitions across resume versions for a specific job.

    Args:
        job_id: ID of the target job description.
        user_id: Authenticated user ID.
        db: Async database session.

    Returns:
        ResumeProgressResponse with timeline, improvement delta, and gained skills.
    """
    # 1. Fetch job
    job_res = await db.execute(
        select(JobDescription).where(JobDescription.id == job_id)
    )
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    # 2. Fetch all matches for this user and job, chronologically
    matches_res = await db.execute(
        select(MatchResult, Resume.file_name)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .where(
            MatchResult.job_id == job_id,
            MatchResult.user_id == user_id,
        )
        .order_by(MatchResult.created_at.asc())
    )
    results = matches_res.all()

    if not results:
        return ResumeProgressResponse(
            job_id=job.id,
            job_title=job.title,
            job_company=job.company,
            total_evaluations=0,
            initial_score=None,
            latest_score=None,
            score_improvement=None,
            average_score=None,
            skills_gained=[],
            timeline=[],
        )

    timeline: list[TimelineMatchEntry] = []
    scores: list[float] = []

    for match, file_name in results:
        score = match.overall_score or 0.0
        scores.append(score)
        timeline.append(
            TimelineMatchEntry(
                match_id=match.id,
                resume_id=match.resume_id,
                resume_file_name=file_name,
                overall_score=score,
                similarity_score=match.similarity_score,
                keyword_score=match.keyword_score,
                missing_keywords=match.missing_keywords,
                created_at=match.created_at,
            )
        )

    initial_score = scores[0]
    latest_score = scores[-1]
    score_improvement = round(latest_score - initial_score, 2)
    average_score = round(sum(scores) / len(scores), 2)

    # Calculate skills gained: missing in earliest version, but no longer missing in latest version
    earliest_missing = set(results[0][0].missing_keywords or [])
    latest_missing = set(results[-1][0].missing_keywords or [])
    skills_gained = sorted(list(earliest_missing - latest_missing))

    return ResumeProgressResponse(
        job_id=job.id,
        job_title=job.title,
        job_company=job.company,
        total_evaluations=len(results),
        initial_score=initial_score,
        latest_score=latest_score,
        score_improvement=score_improvement,
        average_score=average_score,
        skills_gained=skills_gained,
        timeline=timeline,
    )


async def get_resume_evaluations_summary(
    resume_id: int,
    user_id: int,
    db: AsyncSession,
) -> ResumeEvaluationsSummaryResponse:
    """Summarize match scores and job performance for a specific resume across all evaluated jobs.

    Args:
        resume_id: ID of the resume.
        user_id: Authenticated user ID.
        db: Async database session.

    Returns:
        ResumeEvaluationsSummaryResponse detailing performance across jobs.
    """
    resume_res = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == user_id,
        )
    )
    resume = resume_res.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    matches_res = await db.execute(
        select(MatchResult, JobDescription.title, JobDescription.company)
        .join(JobDescription, MatchResult.job_id == JobDescription.id)
        .where(
            MatchResult.resume_id == resume_id,
            MatchResult.user_id == user_id,
        )
        .order_by(MatchResult.created_at.desc())
    )
    results = matches_res.all()

    if not results:
        return ResumeEvaluationsSummaryResponse(
            resume_id=resume.id,
            resume_file_name=resume.file_name,
            total_jobs_matched=0,
            average_score=None,
            highest_score=None,
            lowest_score=None,
            matches=[],
        )

    entries: list[ResumeJobEvaluationEntry] = []
    scores: list[float] = []

    for match, job_title, job_company in results:
        score = match.overall_score or 0.0
        scores.append(score)
        entries.append(
            ResumeJobEvaluationEntry(
                job_id=match.job_id,
                job_title=job_title,
                job_company=job_company,
                overall_score=score,
                similarity_score=match.similarity_score,
                keyword_score=match.keyword_score,
                created_at=match.created_at,
            )
        )

    return ResumeEvaluationsSummaryResponse(
        resume_id=resume.id,
        resume_file_name=resume.file_name,
        total_jobs_matched=len(results),
        average_score=round(sum(scores) / len(scores), 2),
        highest_score=max(scores),
        lowest_score=min(scores),
        matches=entries,
    )


async def get_user_analytics_dashboard(
    user_id: int,
    db: AsyncSession,
) -> UserAnalyticsDashboardResponse:
    """Compute high-level ATS dashboard analytics and skill gap distributions for the user.

    Args:
        user_id: Authenticated user ID.
        db: Async database session.

    Returns:
        UserAnalyticsDashboardResponse containing metrics and top skill gaps.
    """
    # 1. Total resumes
    resumes_count = await db.scalar(
        select(func.count(Resume.id)).where(Resume.user_id == user_id)
    ) or 0

    # 2. Total jobs
    jobs_count = await db.scalar(
        select(func.count(JobDescription.id)).where(JobDescription.user_id == user_id)
    ) or 0

    # 3. Matches
    matches_res = await db.execute(
        select(MatchResult, Resume.file_name)
        .join(Resume, MatchResult.resume_id == Resume.id)
        .where(MatchResult.user_id == user_id)
        .order_by(MatchResult.created_at.desc())
    )
    all_matches = matches_res.all()
    total_matches = len(all_matches)

    if total_matches == 0:
        return UserAnalyticsDashboardResponse(
            total_resumes=resumes_count,
            total_jobs=jobs_count,
            total_matches=0,
            average_match_score=None,
            highest_match_score=None,
            lowest_match_score=None,
            top_missing_skills=[],
            top_candidate_skills=[],
            recent_matches=[],
        )

    scores = [m.overall_score for m, _ in all_matches if m.overall_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else None
    highest_score = max(scores) if scores else None
    lowest_score = min(scores) if scores else None

    # Aggregate missing skill frequencies across all user matches
    missing_counter: Counter[str] = Counter()
    for match, _ in all_matches:
        if match.missing_keywords:
            for skill in match.missing_keywords:
                missing_counter[skill.lower()] += 1

    top_missing = [
        SkillFrequency(
            skill=skill,
            count=count,
            percentage=round((count / total_matches) * 100, 1),
        )
        for skill, count in missing_counter.most_common(10)
    ]

    # Aggregate candidate skills across resumes
    user_resumes = await db.execute(
        select(Resume.parsed_skills).where(Resume.user_id == user_id)
    )
    candidate_counter: Counter[str] = Counter()
    resumes_with_skills = 0
    for row in user_resumes.scalars():
        if row:
            resumes_with_skills += 1
            for skill in row:
                candidate_counter[skill.lower()] += 1

    top_candidate = [
        SkillFrequency(
            skill=skill,
            count=count,
            percentage=round((count / max(1, resumes_with_skills)) * 100, 1),
        )
        for skill, count in candidate_counter.most_common(10)
    ]

    # Recent 5 matches
    recent_matches = [
        TimelineMatchEntry(
            match_id=m.id,
            resume_id=m.resume_id,
            resume_file_name=fname,
            overall_score=m.overall_score or 0.0,
            similarity_score=m.similarity_score,
            keyword_score=m.keyword_score,
            missing_keywords=m.missing_keywords,
            created_at=m.created_at,
        )
        for m, fname in all_matches[:5]
    ]

    return UserAnalyticsDashboardResponse(
        total_resumes=resumes_count,
        total_jobs=jobs_count,
        total_matches=total_matches,
        average_match_score=avg_score,
        highest_match_score=highest_score,
        lowest_match_score=lowest_score,
        top_missing_skills=top_missing,
        top_candidate_skills=top_candidate,
        recent_matches=recent_matches,
    )
