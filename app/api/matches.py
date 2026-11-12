import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.schemas.match import MatchResponse, MatchListResponse
from app.schemas.llm import MatchFeedbackRequest, MatchFeedbackResponse

router = APIRouter()


@router.post(
    "/match/{resume_id}/{job_id}",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run a resume-job match",
)
async def run_match(
    resume_id: int,
    job_id: int,
    generate_feedback: bool = Query(
        False, description="Whether to generate AI recommendations via OpenRouter"
    ),
    model: str | None = Query(
        None, description="Optional OpenRouter model override"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute match score between a resume and a job description.

    - Verifies ownership of both resume and job
    - Checks Redis cache for existing result
    - Computes semantic similarity (cosine via pgvector)
    - Computes keyword overlap
    - Optionally generates AI feedback via OpenRouter
    - Caches and stores the result
    """
    # Verify resume belongs to user
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

    # Verify job belongs to user
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

    # Phase 6: Rate limiting — 10 match requests per minute per user
    from app.core.rate_limiter import check_rate_limit

    await check_rate_limit(current_user.id, action="match")

    # Phase 6: Check Redis cache for existing match result
    from app.services.cache_service import get_cached_match, set_cached_match

    cached = await get_cached_match(resume_id, job_id)
    if cached:
        # Return the cached match — look up the DB record by ID
        cached_id = cached.get("id")
        if cached_id:
            result = await db.execute(
                select(MatchResult).where(MatchResult.id == cached_id)
            )
            cached_match = result.scalar_one_or_none()
            if cached_match:
                # If feedback requested and not present on cached match, generate it now
                if generate_feedback and not cached_match.ai_feedback:
                    from app.services.llm_service import generate_match_feedback

                    feedback_data = await generate_match_feedback(
                        resume_text=resume.raw_text,
                        job_text=job.raw_text,
                        missing_keywords=cached_match.missing_keywords,
                        section_scores=cached_match.section_scores,
                        overall_score=cached_match.overall_score,
                        model=model,
                    )
                    cached_match.ai_feedback = feedback_data.get("feedback_text")
                    await db.commit()
                    await db.refresh(cached_match)
                return cached_match

    # Ensure embeddings exist for both (generates if missing)
    from app.services.matching_service import compute_similarity_score, ensure_embedding

    await ensure_embedding(resume, db)
    await ensure_embedding(job, db)

    # Phase 4: Compute semantic similarity via pgvector
    similarity_score = await compute_similarity_score(resume, job, db)

    # Phase 5: Keyword extraction + gap analysis
    from app.services.keyword_service import (
        extract_skills,
        compute_keyword_overlap,
        find_missing_keywords,
        compute_section_scores,
    )

    # Extract skills (use cached parsed_skills if available, else extract now)
    resume_skills = resume.parsed_skills or extract_skills(resume.raw_text)
    job_skills = job.parsed_skills or extract_skills(job.raw_text)

    # Update parsed_skills if not already stored
    if not resume.parsed_skills:
        resume.parsed_skills = resume_skills
        await db.flush()
    if not job.parsed_skills:
        job.parsed_skills = job_skills
        await db.flush()

    # Compute keyword overlap and missing keywords
    keyword_score = compute_keyword_overlap(resume_skills, job_skills)
    missing_keywords = find_missing_keywords(resume_skills, job_skills)

    # Section-level breakdown
    section_scores = compute_section_scores(
        resume_skills, job_skills, resume.raw_text, job.raw_text
    )

    # Combined score: 60% semantic + 40% keyword
    overall_score = (similarity_score * 0.6) + (keyword_score * 0.4)

    # Phase 8: Generate AI feedback via OpenRouter if requested
    ai_feedback_text = None
    if generate_feedback:
        from app.services.llm_service import generate_match_feedback

        feedback_data = await generate_match_feedback(
            resume_text=resume.raw_text,
            job_text=job.raw_text,
            missing_keywords=missing_keywords,
            section_scores=section_scores,
            overall_score=round(overall_score * 100, 2),
            model=model,
        )
        ai_feedback_text = feedback_data.get("feedback_text")

    # Store the match result
    match_result = MatchResult(
        resume_id=resume_id,
        job_id=job_id,
        user_id=current_user.id,
        similarity_score=round(similarity_score * 100, 2),
        keyword_score=round(keyword_score * 100, 2),
        overall_score=round(overall_score * 100, 2),
        section_scores=section_scores,
        missing_keywords=missing_keywords if missing_keywords else None,
        ai_feedback=ai_feedback_text,
    )
    db.add(match_result)
    await db.flush()
    await db.refresh(match_result)

    # Cache the result in Redis (1-hour TTL)
    await set_cached_match(
        resume_id,
        job_id,
        current_user.id,
        {"id": match_result.id, "created_at": match_result.created_at},
    )

    return match_result



@router.get(
    "/matches",
    response_model=list[MatchListResponse],
    summary="List all match results with filtering, sorting, and pagination",
)
async def list_matches(
    response: Response,
    resume_id: int | None = Query(None, description="Filter matches by resume ID"),
    job_id: int | None = Query(None, description="Filter matches by job ID"),
    min_score: float | None = Query(None, ge=0.0, le=100.0, description="Minimum overall match score"),
    sort_by: str = Query(
        "date_desc",
        description="Sort order: 'date_desc', 'date_asc', 'score_desc', 'score_asc'",
    ),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of matches to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List match results for the authenticated user with optional filtering, sorting, and pagination."""
    query = select(MatchResult).where(MatchResult.user_id == current_user.id)
    count_query = select(func.count(MatchResult.id)).where(MatchResult.user_id == current_user.id)

    if resume_id is not None:
        query = query.where(MatchResult.resume_id == resume_id)
        count_query = count_query.where(MatchResult.resume_id == resume_id)

    if job_id is not None:
        query = query.where(MatchResult.job_id == job_id)
        count_query = count_query.where(MatchResult.job_id == job_id)

    if min_score is not None:
        query = query.where(MatchResult.overall_score >= min_score)
        count_query = count_query.where(MatchResult.overall_score >= min_score)

    total_count = await db.scalar(count_query) or 0
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Limit"] = str(limit)
    response.headers["X-Offset"] = str(offset)

    if sort_by == "date_asc":
        query = query.order_by(MatchResult.created_at.asc())
    elif sort_by == "score_desc":
        query = query.order_by(MatchResult.overall_score.desc())
    elif sort_by == "score_asc":
        query = query.order_by(MatchResult.overall_score.asc())
    else:  # default date_desc
        query = query.order_by(MatchResult.created_at.desc())

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get(
    "/matches/{match_id}",
    response_model=MatchResponse,
    summary="Get match result details",
)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed match result including AI feedback."""
    result = await db.execute(
        select(MatchResult).where(
            MatchResult.id == match_id,
            MatchResult.user_id == current_user.id,
        )
    )
    match_result = result.scalar_one_or_none()

    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found",
        )

    return match_result


@router.get(
    "/matches/{match_id}/export-pdf",
    summary="Export assessment and AI recommendations as a styled PDF report",
)
@router.get(
    "/matches/{match_id}/pdf",
    include_in_schema=False,
)
async def export_match_pdf(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and stream a professional PDF assessment report for a match result.

    Includes score summaries, section-level assessments, skill gaps,
    and tailored AI improvement suggestions.
    """
    result = await db.execute(
        select(MatchResult).where(
            MatchResult.id == match_id,
            MatchResult.user_id == current_user.id,
        )
    )
    match_result = result.scalar_one_or_none()
    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found",
        )

    resume_res = await db.execute(
        select(Resume).where(Resume.id == match_result.resume_id)
    )
    resume = resume_res.scalar_one_or_none()

    job_res = await db.execute(
        select(JobDescription).where(JobDescription.id == match_result.job_id)
    )
    job = job_res.scalar_one_or_none()

    if not resume or not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated resume or job not found",
        )

    from io import BytesIO
    from app.services.pdf_export_service import generate_match_report_pdf

    pdf_bytes = generate_match_report_pdf(match_result, resume, job)
    filename = f"ATS_Match_Report_Match_{match_id}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.post(
    "/matches/{match_id}/feedback",
    response_model=MatchFeedbackResponse,
    summary="Generate or regenerate AI feedback for a match",
)
async def generate_feedback_for_match(
    match_id: int,
    payload: MatchFeedbackRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate structured AI recommendations, strengths, and bullet rewrites for a match."""
    result = await db.execute(
        select(MatchResult).where(
            MatchResult.id == match_id,
            MatchResult.user_id == current_user.id,
        )
    )
    match_result = result.scalar_one_or_none()
    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found",
        )

    # Fetch associated resume and job
    resume_res = await db.execute(
        select(Resume).where(Resume.id == match_result.resume_id)
    )
    resume = resume_res.scalar_one_or_none()

    job_res = await db.execute(
        select(JobDescription).where(JobDescription.id == match_result.job_id)
    )
    job = job_res.scalar_one_or_none()

    if not resume or not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated resume or job description not found",
        )

    from app.services.llm_service import generate_match_feedback

    model_override = payload.model if payload else None
    feedback_data = await generate_match_feedback(
        resume_text=resume.raw_text,
        job_text=job.raw_text,
        missing_keywords=match_result.missing_keywords,
        section_scores=match_result.section_scores,
        overall_score=match_result.overall_score,
        model=model_override,
    )

    feedback_text = feedback_data.get("feedback_text", "")
    match_result.ai_feedback = feedback_text
    await db.commit()
    await db.refresh(match_result)

    return MatchFeedbackResponse(
        match_id=match_id,
        ai_feedback=feedback_text,
        model_used=feedback_data.get("model_used", "unknown"),
        fallback_used=feedback_data.get("fallback_used", False),
    )


@router.get(
    "/matches/{match_id}/feedback/stream",
    summary="Stream AI feedback for a match token-by-token (SSE)",
)
async def stream_match_feedback(
    match_id: int,
    model: str | None = Query(None, description="Optional OpenRouter model override"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream AI improvement suggestions in real time token-by-token using Server-Sent Events (SSE)."""
    result = await db.execute(
        select(MatchResult).where(
            MatchResult.id == match_id,
            MatchResult.user_id == current_user.id,
        )
    )
    match_result = result.scalar_one_or_none()
    if not match_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match result not found",
        )

    resume_res = await db.execute(
        select(Resume).where(Resume.id == match_result.resume_id)
    )
    resume = resume_res.scalar_one_or_none()

    job_res = await db.execute(
        select(JobDescription).where(JobDescription.id == match_result.job_id)
    )
    job = job_res.scalar_one_or_none()

    if not resume or not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated resume or job not found",
        )

    from app.services.llm_service import stream_openrouter, SYSTEM_PROMPT_MATCH_FEEDBACK

    prompt = (
        f"RESUME:\n{resume.raw_text[:2000]}\n\n"
        f"JOB DESCRIPTION:\n{job.raw_text[:2000]}\n\n"
        f"OVERALL SCORE: {match_result.overall_score}%\n"
        f"MISSING SKILLS: {', '.join(match_result.missing_keywords or [])}\n\n"
        "Provide 3-5 specific, actionable bullet-point rewrites and strategic ATS recommendations."
    )

    async def sse_event_stream():
        accumulated = []
        async for token in stream_openrouter(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT_MATCH_FEEDBACK,
            model=model,
        ):
            accumulated.append(token)
            yield f"data: {json.dumps({'token': token})}\n\n"

        full_text = "".join(accumulated)
        if full_text and not match_result.ai_feedback:
            try:
                match_result.ai_feedback = full_text
                await db.commit()
            except Exception:
                pass

        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_event_stream(), media_type="text/event-stream")

