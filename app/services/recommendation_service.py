"""Recommendation service — ranks stored job descriptions by pgvector similarity to a resume.

Leverages PostgreSQL pgvector cosine distance operator (<=>) for high-performance
nearest-neighbor search across stored job vectors, blended with keyword analysis.
"""

import logging
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.resume import Resume
from app.models.job import JobDescription
from app.services.matching_service import ensure_embedding
from app.services.keyword_service import (
    compute_keyword_overlap,
    find_missing_keywords,
    extract_skills,
)
from app.schemas.recommendation import (
    JobRecommendationItem,
    JobRecommendationsResponse,
)

logger = logging.getLogger(__name__)


async def get_job_recommendations_for_resume(
    resume_id: int,
    current_user_id: int,
    db: AsyncSession,
    limit: int = 5,
    offset: int = 0,
    min_similarity: float = 0.0,
    include_all_jobs: bool = True,
) -> JobRecommendationsResponse:
    """Find and rank stored job descriptions by semantic similarity to a resume.

    Args:
        resume_id: ID of the candidate's resume.
        current_user_id: Authenticated user ID (must own the resume).
        db: Async database session.
        limit: Maximum number of job recommendations to return.
        offset: Pagination offset.
        min_similarity: Minimum cosine similarity threshold (0.0 to 1.0 or 0 to 100).
        include_all_jobs: If True, searches across all stored jobs in the database;
                          if False, only searches jobs uploaded by current_user.

    Returns:
        JobRecommendationsResponse containing ranked recommendations with full score breakdowns.
    """
    # 1. Fetch resume and verify ownership
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user_id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    # 2. Ensure resume has an embedding
    await ensure_embedding(resume, db)
    if not resume.parsed_skills:
        resume.parsed_skills = extract_skills(resume.raw_text)
        await db.flush()

    # Convert percentage threshold to 0.0-1.0 if passed as 0-100
    sim_threshold = min_similarity / 100.0 if min_similarity > 1.0 else min_similarity

    # 3. Count total candidate jobs
    count_query = select(func.count(JobDescription.id)).where(
        JobDescription.embedding.isnot(None)
    )
    if not include_all_jobs:
        count_query = count_query.where(JobDescription.user_id == current_user_id)

    count_res = await db.execute(count_query)
    total_jobs_evaluated = count_res.scalar() or 0

    if total_jobs_evaluated == 0:
        return JobRecommendationsResponse(
            resume_id=resume.id,
            resume_file_name=resume.file_name,
            total_jobs_evaluated=0,
            returned_count=0,
            recommendations=[],
        )

    # 4. Nearest-neighbor pgvector search
    user_clause = "AND j.user_id = :filter_user_id" if not include_all_jobs else ""
    params = {
        "resume_id": resume.id,
        "min_sim": float(sim_threshold),
        "limit": int(limit),
        "offset": int(offset),
    }
    if not include_all_jobs:
        params["filter_user_id"] = current_user_id

    query = text(f"""
        SELECT 
            j.id,
            j.title,
            j.company,
            j.raw_text,
            j.parsed_skills,
            j.created_at,
            1 - (j.embedding <=> r.embedding) AS similarity
        FROM job_descriptions j, resumes r
        WHERE r.id = :resume_id
          AND j.embedding IS NOT NULL
          AND r.embedding IS NOT NULL
          {user_clause}
          AND (1 - (j.embedding <=> r.embedding)) >= :min_sim
        ORDER BY j.embedding <=> r.embedding ASC
        LIMIT :limit OFFSET :offset
    """)

    db_result = await db.execute(query, params)
    rows = db_result.fetchall()

    resume_skills = resume.parsed_skills or []
    recommendations: list[JobRecommendationItem] = []

    for row in rows:
        sim_score = max(0.0, min(1.0, float(row.similarity)))
        sim_pct = round(sim_score * 100, 2)

        job_skills = row.parsed_skills
        if not job_skills:
            job_skills = extract_skills(row.raw_text)

        keyword_overlap = compute_keyword_overlap(resume_skills, job_skills)
        keyword_pct = round(keyword_overlap * 100, 2)

        # 60% semantic similarity + 40% keyword overlap
        overall_score = round((0.6 * sim_pct) + (0.4 * keyword_pct), 2)

        matching_skills = sorted(list(set(resume_skills) & set(job_skills)))
        missing_skills = find_missing_keywords(resume_skills, job_skills)

        recommendations.append(
            JobRecommendationItem(
                job_id=row.id,
                title=row.title,
                company=row.company,
                similarity_score=sim_pct,
                keyword_score=keyword_pct,
                overall_score=overall_score,
                matching_skills=matching_skills,
                missing_skills=missing_skills,
                created_at=row.created_at,
            )
        )

    # Sort recommendations by overall score descending
    recommendations.sort(key=lambda r: r.overall_score, reverse=True)

    return JobRecommendationsResponse(
        resume_id=resume.id,
        resume_file_name=resume.file_name,
        total_jobs_evaluated=total_jobs_evaluated,
        returned_count=len(recommendations),
        recommendations=recommendations,
    )
