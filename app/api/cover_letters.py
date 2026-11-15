"""Cover letter endpoints (Phase 14).

CRUD + duplicate mirror the documents API. The generation endpoint is the
one-click flow from the roadmap's acceptance criteria: pick a resume
(uploaded, or a built document) and a job (saved or pasted) → a saved,
editable letter draft in the editor — never a dead-end text box.
"""

import copy
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.cover_letter import CoverLetter
from app.models.job import JobDescription
from app.models.resume import Resume
from app.models.resume_document import ResumeDocument
from app.models.user import User
from app.schemas.cover_letter import (
    CoverLetterCreate,
    CoverLetterGenerateRequest,
    CoverLetterListItem,
    CoverLetterResponse,
    CoverLetterUpdate,
)
from app.services.document_service import flatten_content_to_text
from app.services.llm_service import generate_cover_letter

router = APIRouter()


async def _get_owned_letter(db: AsyncSession, letter_id: int, user: User) -> CoverLetter:
    result = await db.execute(
        select(CoverLetter).where(
            CoverLetter.id == letter_id, CoverLetter.user_id == user.id
        )
    )
    letter = result.scalar_one_or_none()
    if letter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cover letter not found"
        )
    return letter


@router.post("", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED, summary="Create a cover letter")
async def create_letter(
    payload: CoverLetterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    letter = CoverLetter(
        user_id=current_user.id,
        title=payload.title,
        template_id=payload.template_id,
        theme=payload.theme,
        content=payload.content,
        resume_id=payload.resume_id,
        resume_document_id=payload.resume_document_id,
        job_id=payload.job_id,
    )
    db.add(letter)
    await db.commit()
    await db.refresh(letter)
    return letter


@router.get("", response_model=list[CoverLetterListItem], summary="List cover letters")
async def list_letters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoverLetter)
        .where(CoverLetter.user_id == current_user.id)
        .order_by(desc(CoverLetter.updated_at))
    )
    return result.scalars().all()


@router.post("/generate", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED, summary="Generate a cover letter draft from a resume + job")
async def generate_letter(
    payload: CoverLetterGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate + persist a letter draft (the one-click matcher flow).

    Resume source: an uploaded resume, or a built document (its *current*
    content is flattened — a letter should reflect the document as it is now,
    not a stale sync). Job source: a saved job, or pasted text.
    """
    # ── Resolve the resume ──
    resume_text = ""
    sender: dict = {}
    resume_id = payload.resume_id
    document_id = payload.resume_document_id

    if document_id:
        result = await db.execute(
            select(ResumeDocument).where(
                ResumeDocument.id == document_id,
                ResumeDocument.user_id == current_user.id,
            )
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        resume_text = flatten_content_to_text(document.content)
        personal = (document.content or {}).get("personal") or {}
        sender = {
            "name": personal.get("full_name", ""),
            "title": personal.get("title", ""),
            "email": personal.get("email", ""),
            "phone": personal.get("phone", ""),
            "location": personal.get("location", ""),
        }
        resume_id = document.resume_id or resume_id
        template_id = payload.template_id if payload.template_id != "classic" else document.template_id
    elif resume_id:
        result = await db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
        )
        resume = result.scalar_one_or_none()
        if resume is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        resume_text = resume.raw_text
        template_id = payload.template_id
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide resume_id or resume_document_id",
        )

    if len(resume_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The source resume has too little content to write a letter from",
        )
    if not sender:
        lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
        sender = {
            "name": lines[0] if lines else "",
            "title": lines[1] if len(lines) > 1 and "@" not in lines[1] else "",
            "email": current_user.email,
            "phone": "",
            "location": "",
        }

    # ── Resolve the job ──
    job_text = payload.job_text or ""
    job_title = payload.job_title or ""
    company = payload.company or ""
    job_id = payload.job_id
    if job_id:
        result = await db.execute(
            select(JobDescription).where(
                JobDescription.id == job_id, JobDescription.user_id == current_user.id
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        job_text = job.raw_text
        job_title = job.title or job_title
        company = job.company or company
    if len(job_text.strip()) < 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide job_id or job_text (at least a short description)",
        )

    # ── Generate ──
    generated = await generate_cover_letter(
        resume_text=resume_text,
        job_text=job_text,
        job_title=job_title,
        company=company,
        tone=payload.tone,
        model=payload.model,
    )

    recipient_name = (payload.recipient_name or "").strip()
    content = {
        "sender": sender,
        "recipient": {"name": recipient_name, "company": company, "role": job_title},
        "date": date.today().isoformat(),
        "greeting": f"Dear {recipient_name}," if recipient_name else "Dear Hiring Manager,",
        "paragraphs": generated["paragraphs"],
        "closing": "Sincerely,",
        "signature_name": sender.get("name", ""),
    }
    title_bits = [job_title, company]
    title = "Cover letter — " + " at ".join(b for b in title_bits if b) if any(title_bits) else "Cover letter"

    letter = CoverLetter(
        user_id=current_user.id,
        title=title,
        template_id=template_id,
        theme={},
        content=content,
        resume_id=resume_id,
        resume_document_id=document_id,
        job_id=job_id,
    )
    db.add(letter)
    await db.commit()
    await db.refresh(letter)
    return letter


@router.get("/{letter_id}", response_model=CoverLetterResponse, summary="Get a cover letter")
async def get_letter(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_letter(db, letter_id, current_user)


@router.put("/{letter_id}", response_model=CoverLetterResponse, summary="Update a cover letter")
async def update_letter(
    letter_id: int,
    payload: CoverLetterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    letter = await _get_owned_letter(db, letter_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(letter, field, value)
    await db.commit()
    await db.refresh(letter)
    return letter


@router.delete("/{letter_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a cover letter")
async def delete_letter(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    letter = await _get_owned_letter(db, letter_id, current_user)
    await db.delete(letter)
    await db.commit()
    return None


@router.post("/{letter_id}/duplicate", response_model=CoverLetterResponse, status_code=status.HTTP_201_CREATED, summary="Duplicate a cover letter")
async def duplicate_letter(
    letter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = await _get_owned_letter(db, letter_id, current_user)
    letter = CoverLetter(
        user_id=current_user.id,
        title=f"{source.title} (copy)",
        template_id=source.template_id,
        theme=copy.deepcopy(source.theme),
        content=copy.deepcopy(source.content),
        resume_id=source.resume_id,
        resume_document_id=source.resume_document_id,
        job_id=source.job_id,
    )
    db.add(letter)
    await db.commit()
    await db.refresh(letter)
    return letter
