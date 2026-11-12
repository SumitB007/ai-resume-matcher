"""Resume endpoints — upload, list, and get resume details."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeListResponse
from app.schemas.task import ItemStatusResponse
from app.schemas.recommendation import JobRecommendationsResponse
from app.services.recommendation_service import get_job_recommendations_for_resume

router = APIRouter()

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume",
)
async def upload_resume(
    file: UploadFile = File(..., description="Resume file (PDF or DOCX)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a resume file (PDF or DOCX).

    - Validates file type and size
    - Extracts raw text from the document
    - Stores in database with status 'pending'
    - Dispatches background Celery task to parse skills + generate embeddings
    """
    # Validate file extension
    file_ext = ""
    if file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    # Extract text based on file type
    if file_ext == ".pdf":
        from app.utils.pdf_parser import extract_text_from_pdf

        raw_text = extract_text_from_pdf(content)
    elif file_ext == ".docx":
        from app.utils.docx_parser import extract_text_from_docx

        raw_text = extract_text_from_docx(content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format",
        )

    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract sufficient text from the uploaded file",
        )

    # Extract initial skills from the resume text
    from app.services.keyword_service import extract_skills

    parsed_skills = extract_skills(raw_text)

    # Create resume record in pending status
    resume = Resume(
        user_id=current_user.id,
        raw_text=raw_text,
        file_name=file.filename,
        parsed_skills=parsed_skills,
        status="pending",
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    # Phase 7: Dispatch background Celery task for embedding and processing
    from app.tasks.resume_tasks import process_resume_task

    try:
        task = process_resume_task.delay(resume.id)
        resume.task_id = task.id
        await db.commit()
        await db.refresh(resume)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to dispatch Celery task for resume {resume.id}: {e}")

    return resume



@router.get(
    "",
    response_model=list[ResumeListResponse],
    summary="List all resumes for current user",
)
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resumes uploaded by the authenticated user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{resume_id}/recommendations",
    response_model=JobRecommendationsResponse,
    summary="Rank stored jobs by similarity to this resume (pgvector nearest-neighbor search)",
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
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get resume details",
)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific resume."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return resume


@router.get(
    "/{resume_id}/status",
    response_model=ItemStatusResponse,
    summary="Get resume background processing status",
)
async def get_resume_status(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check processing status of a resume and whether embeddings are ready."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    return ItemStatusResponse(
        id=resume.id,
        item_type="resume",
        status=resume.status,
        task_id=resume.task_id,
        has_embedding=resume.embedding is not None,
        skills_count=len(resume.parsed_skills or []),
    )


@router.post(
    "/{resume_id}/reprocess",
    response_model=ItemStatusResponse,
    summary="Trigger background reprocessing for a resume",
)
async def reprocess_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger background Celery task to re-extract skills and regenerate embedding."""
    result = await db.execute(
        select(Resume).where(
            Resume.id == resume_id,
            Resume.user_id == current_user.id,
        )
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found",
        )

    from app.tasks.resume_tasks import process_resume_task

    resume.status = "pending"
    await db.commit()

    task = process_resume_task.delay(resume.id)
    resume.task_id = task.id
    await db.commit()
    await db.refresh(resume)

    return ItemStatusResponse(

        id=resume.id,
        item_type="resume",
        status=resume.status,
        task_id=resume.task_id,
        has_embedding=resume.embedding is not None,
        skills_count=len(resume.parsed_skills or []),
    )

