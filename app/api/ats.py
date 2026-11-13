"""ATS checker endpoints (Phase 11 — roadmap Phase 2).

Two surfaces, one engine (app/services/ats_service.py):
- Authenticated: run a check on a resume you own (persisted), fetch the latest.
- Anonymous: the public free checker. Parses the upload in-memory and returns
  the result WITHOUT persisting anything — the resume text and the result
  never touch the database (decisions.md §12.3).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.ats_check import AtsCheckResult
from app.models.resume import Resume
from app.models.user import User
from app.schemas.ats import AtsCheckResponse
from app.services.ats_service import run_ats_checks

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB — mirrors app/api/resumes.py


def _to_response(row: AtsCheckResult) -> AtsCheckResponse:
    return AtsCheckResponse(
        id=row.id,
        resume_id=row.resume_id,
        score=row.score,
        groups=row.result["groups"],
        checks=row.result["checks"],
        word_count=row.result["word_count"],
        skills_found=row.result["skills_found"],
        created_at=row.created_at,
    )


async def _get_owned_resume(db: AsyncSession, resume_id: int, user: User) -> Resume:
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    return resume


@router.post(
    "/resumes/{resume_id}/ats-check",
    response_model=AtsCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run an ATS readiness check on a resume",
)
async def run_resume_ats_check(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the rule-based ATS checker against the resume's extracted text.

    Synchronous and instant (no LLM, no embedding) — the result is persisted
    so it can be re-fetched and compared over time.
    """
    resume = await _get_owned_resume(db, resume_id, current_user)
    result = run_ats_checks(resume.raw_text, resume.parsed_skills)

    row = AtsCheckResult(
        user_id=current_user.id,
        resume_id=resume.id,
        score=result["score"],
        result=result,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.get(
    "/resumes/{resume_id}/ats-check",
    response_model=AtsCheckResponse,
    summary="Get the latest ATS check for a resume",
)
async def get_resume_ats_check(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recent persisted ATS check for this resume (404 if none)."""
    await _get_owned_resume(db, resume_id, current_user)
    result = await db.execute(
        select(AtsCheckResult)
        .where(
            AtsCheckResult.resume_id == resume_id,
            AtsCheckResult.user_id == current_user.id,
        )
        .order_by(desc(AtsCheckResult.created_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No ATS check has been run for this resume yet",
        )
    return _to_response(row)


@router.post(
    "/ats/check-upload",
    response_model=AtsCheckResponse,
    summary="Anonymous ATS check — upload a resume, nothing is stored",
)
async def anonymous_ats_check(file: UploadFile = File(..., description="Resume file (PDF or DOCX)")):
    """Public free checker: parse + check in-memory, persist NOTHING.

    Validation mirrors the authenticated upload (type, size, minimum text) so
    the public and signed-in experiences agree.
    """
    file_ext = ""
    if file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if file_ext == ".pdf":
        from app.utils.pdf_parser import extract_text_from_pdf

        raw_text = extract_text_from_pdf(content)
    else:
        from app.utils.docx_parser import extract_text_from_docx

        raw_text = extract_text_from_docx(content)

    if not raw_text or len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract sufficient text from the uploaded file",
        )

    result = run_ats_checks(raw_text)
    return AtsCheckResponse(
        id=None,
        resume_id=None,
        score=result["score"],
        groups=result["groups"],
        checks=result["checks"],
        word_count=result["word_count"],
        skills_found=result["skills_found"],
        created_at=None,
    )
