"""Matching service — computes similarity scores between resumes and job descriptions.

Combines semantic similarity (via embeddings) with keyword overlap
for a comprehensive match score.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.job import JobDescription
from app.services.embedding_service import generate_embedding, compute_cosine_similarity

logger = logging.getLogger(__name__)


async def compute_similarity_score(
    resume: Resume,
    job: JobDescription,
    db: AsyncSession,
) -> float:
    """Compute semantic similarity between a resume and job description.

    Uses pgvector's cosine distance operator (<=>). Falls back to
    Python-based cosine similarity if pgvector query fails.

    Args:
        resume: Resume model with embedding.
        job: JobDescription model with embedding.
        db: Async database session.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    # If either embedding is missing, generate them now
    if resume.embedding is None:
        logger.info(f"Generating embedding for resume {resume.id}...")
        resume.embedding = generate_embedding(resume.raw_text)
        resume.status = "completed"
        await db.flush()

    if job.embedding is None:
        logger.info(f"Generating embedding for job {job.id}...")
        job.embedding = generate_embedding(job.raw_text)
        job.status = "completed"
        await db.flush()

    # Use pgvector's cosine distance operator for DB-native computation
    try:
        result = await db.execute(
            text("""
                SELECT 1 - (
                    (SELECT embedding FROM resumes WHERE id = :resume_id)
                    <=>
                    (SELECT embedding FROM job_descriptions WHERE id = :job_id)
                ) AS similarity
            """),
            {"resume_id": resume.id, "job_id": job.id},
        )
        row = result.fetchone()
        if row and row.similarity is not None:
            similarity = float(row.similarity)
            # Clamp to [0, 1]
            return max(0.0, min(1.0, similarity))
    except Exception as e:
        logger.warning(f"pgvector similarity query failed, falling back to Python: {e}")

    # Fallback: compute in Python
    return compute_cosine_similarity(
        list(resume.embedding), list(job.embedding)
    )


async def ensure_embedding(
    record: Resume | JobDescription,
    db: AsyncSession,
) -> None:
    """Ensure a resume or job description has an embedding vector.

    If the embedding is missing, generates it synchronously and updates the record.

    Args:
        record: A Resume or JobDescription model instance.
        db: Async database session.
    """
    if record.embedding is not None:
        return

    logger.info(f"Generating embedding for {type(record).__name__} {record.id}...")
    record.embedding = generate_embedding(record.raw_text)
    record.status = "completed"
    await db.flush()
    logger.info(f"✅ Embedding generated for {type(record).__name__} {record.id}")
