"""Job description endpoints — create, list, and get job details."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.job import JobDescription
from app.schemas.job import JobCreate, JobResponse, JobListResponse
from app.schemas.task import ItemStatusResponse
from app.schemas.recommendation import JobRecommendationsResponse
from app.services.recommendation_service import get_job_recommendations_for_resume

router = APIRouter()


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a job description",
)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a job description for matching.

    - Stores the raw text, title, and company
    - Sets status to 'pending'
    - Dispatches background Celery task to extract skills + generate embedding
    """
    # Extract initial skills from the job description
    from app.services.keyword_service import extract_skills

    parsed_skills = extract_skills(job_data.raw_text)

    job = JobDescription(
        user_id=current_user.id,
        raw_text=job_data.raw_text,
        title=job_data.title,
        company=job_data.company,
        parsed_skills=parsed_skills,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Phase 7: Dispatch background Celery task for embedding and processing
    from app.tasks.embedding_tasks import process_job_task

    try:
        task = process_job_task.delay(job.id)
        job.task_id = task.id
        await db.commit()
        await db.refresh(job)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to dispatch Celery task for job {job.id}: {e}")

    return job




@router.get(
    "",
    response_model=list[JobListResponse],
    summary="List all jobs for current user",
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all job descriptions submitted by the authenticated user."""
    result = await db.execute(
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{resume_id}/recommendations",
    response_model=JobRecommendationsResponse,
    summary="Rank stored jobs by similarity to a resume (pgvector nearest-neighbor search)",
)
async def recommend_jobs_for_resume(
    resume_id: int,
    limit: int = Query(5, ge=1, le=50, description="Maximum number of recommendations"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    min_similarity: float = Query(
        0.0, ge=0.0, le=100.0, description="Minimum cosine similarity threshold (percentage or 0-1)"
    ),
    include_all_jobs: bool = Query(
        True, description="Search across all catalog jobs (True) or only user's jobs (False)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rank all stored job descriptions by pgvector semantic similarity to this resume.

    Combines 60% cosine vector similarity with 40% keyword overlap,
    returning top matching jobs along with skill gaps and shared competencies.
    """
    return await get_job_recommendations_for_resume(
        resume_id=resume_id,
        current_user_id=current_user.id,
        db=db,
        limit=limit,
        offset=offset,
        min_similarity=min_similarity,
        include_all_jobs=include_all_jobs,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job description details",
)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific job description."""
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    return job


@router.get(
    "/{job_id}/status",
    response_model=ItemStatusResponse,
    summary="Get job description background processing status",
)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check processing status of a job description and whether embeddings are ready."""
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    return ItemStatusResponse(
        id=job.id,
        item_type="job",
        status=job.status,
        task_id=job.task_id,
        has_embedding=job.embedding is not None,
        skills_count=len(job.parsed_skills or []),
    )


@router.post(
    "/{job_id}/reprocess",
    response_model=ItemStatusResponse,
    summary="Trigger background reprocessing for a job description",
)
async def reprocess_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger background Celery task to re-extract skills and regenerate embedding."""
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job description not found",
        )

    from app.tasks.embedding_tasks import process_job_task

    job.status = "pending"
    await db.commit()

    task = process_job_task.delay(job.id)
    job.task_id = task.id
    await db.commit()
    await db.refresh(job)

    return ItemStatusResponse(
        id=job.id,
        item_type="job",
        status=job.status,
        task_id=job.task_id,
        has_embedding=job.embedding is not None,
        skills_count=len(job.parsed_skills or []),
    )


