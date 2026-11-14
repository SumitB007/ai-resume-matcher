"""Resume builder document endpoints (Phase 13).

CRUD + duplicate + import-from-upload, plus the two bridges into the rest of
the product:
- POST /documents/{id}/sync-resume — flatten the document to text and create
  (or update) its pipeline twin Resume, dispatching the existing embedding
  task, so a built resume can be matched and ATS-checked like an upload.
- POST /documents/{id}/ats-check — run the ATS checker on the flattened text
  (live preview score for the editor; not persisted).
"""

import copy

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.resume import Resume
from app.models.resume_document import ResumeDocument
from app.models.user import User
from app.schemas.ats import AtsCheckResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentListItem,
    DocumentResponse,
    DocumentUpdate,
)
from app.schemas.resume import ResumeResponse
from app.services.ats_service import run_ats_checks
from app.services.document_service import flatten_content_to_text, parse_text_to_content
from app.services.keyword_service import extract_skills

router = APIRouter()


async def _get_owned_document(db: AsyncSession, document_id: int, user: User) -> ResumeDocument:
    result = await db.execute(
        select(ResumeDocument).where(
            ResumeDocument.id == document_id, ResumeDocument.user_id == user.id
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Create a resume document")
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = ResumeDocument(
        user_id=current_user.id,
        title=payload.title,
        template_id=payload.template_id,
        theme=payload.theme,
        content=payload.content,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.get("", response_model=list[DocumentListItem], summary="List resume documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ResumeDocument)
        .where(ResumeDocument.user_id == current_user.id)
        .order_by(desc(ResumeDocument.updated_at))
    )
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse, summary="Get a resume document")
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_document(db, document_id, current_user)


@router.put("/{document_id}", response_model=DocumentResponse, summary="Update a resume document")
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await _get_owned_document(db, document_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(document, field, value)
    await db.commit()
    await db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a resume document")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await _get_owned_document(db, document_id, current_user)
    await db.delete(document)
    await db.commit()
    return None


@router.post("/{document_id}/duplicate", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Duplicate a resume document")
async def duplicate_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Copy the document (content deep-copied). The copy starts unsynced —
    it gets its own pipeline twin only when the user syncs it."""
    source = await _get_owned_document(db, document_id, current_user)
    document = ResumeDocument(
        user_id=current_user.id,
        title=f"{source.title} (copy)",
        template_id=source.template_id,
        theme=copy.deepcopy(source.theme),
        content=copy.deepcopy(source.content),
        resume_id=None,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.post("/import-from-resume/{resume_id}", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, summary="Import an uploaded resume into the builder")
async def import_from_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a draft document from an uploaded resume's extracted text.

    Heuristic parse (document_service.parse_text_to_content): always lands as
    a draft for review in the editor, never silently 'final'."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found"
        )
    content = parse_text_to_content(resume.raw_text)
    document = ResumeDocument(
        user_id=current_user.id,
        title=(resume.file_name or "Imported resume").rsplit(".", 1)[0],
        template_id="classic",
        theme={},
        content=content,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document


@router.post("/{document_id}/sync-resume", response_model=ResumeResponse, summary="Sync a document into the matching pipeline")
async def sync_resume(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Flatten the document and create/update its twin Resume row.

    Mirrors the upload flow (app/api/resumes.py): commit BEFORE dispatching
    the Celery embedding task so the worker can see the row (Phase 7, §7.2).
    """
    document = await _get_owned_document(db, document_id, current_user)
    raw_text = flatten_content_to_text(document.content)
    if len(raw_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Document is too empty to sync — add more content first",
        )

    if document.resume_id:
        result = await db.execute(
            select(Resume).where(
                Resume.id == document.resume_id, Resume.user_id == current_user.id
            )
        )
        resume = result.scalar_one_or_none()
    else:
        resume = None

    if resume is None:
        resume = Resume(user_id=current_user.id, status="pending")
        db.add(resume)

    resume.raw_text = raw_text
    resume.file_name = f"{document.title} (built)"
    resume.parsed_skills = extract_skills(raw_text)
    resume.status = "pending"
    await db.commit()
    await db.refresh(resume)

    document.resume_id = resume.id
    await db.commit()

    # Existing matches against this resume are now stale — drop cached ones.
    from app.services.cache_service import invalidate_user_matches

    await invalidate_user_matches(current_user.id)

    from app.tasks.resume_tasks import process_resume_task

    try:
        task = process_resume_task.delay(resume.id)
        resume.task_id = task.id
        await db.commit()
        await db.refresh(resume)
    except Exception as e:
        import logging

        logging.getLogger(__name__).warning(
            f"Failed to dispatch Celery task for synced resume {resume.id}: {e}"
        )

    return resume


@router.post("/{document_id}/ats-check", response_model=AtsCheckResponse, summary="Live ATS check for a document (not persisted)")
async def document_ats_check(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ATS-check the document's flattened text — the editor's live score."""
    document = await _get_owned_document(db, document_id, current_user)
    raw_text = flatten_content_to_text(document.content)
    skills = extract_skills(raw_text)
    result = run_ats_checks(raw_text, skills)
    return AtsCheckResponse(
        id=None,
        resume_id=document.resume_id,
        score=result["score"],
        groups=result["groups"],
        checks=result["checks"],
        word_count=result["word_count"],
        skills_found=result["skills_found"],
        created_at=None,
    )
