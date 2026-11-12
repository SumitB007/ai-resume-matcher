"""Embedding background tasks — vector generation for job descriptions and batch operations."""

import logging
from celery import shared_task

from app.database import get_sync_db
from app.models.job import JobDescription
from app.models.resume import Resume
from app.services.keyword_service import extract_skills
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.tasks.embedding_tasks.process_job_task")
def process_job_task(self, job_id: int) -> dict:
    """Background task to process a job description:

    1. Updates status to 'processing'
    2. Extracts skills from raw text (if not already extracted)
    3. Generates 384-dimensional vector embedding via Sentence-Transformers
    4. Updates database record with embedding, skills, and status 'completed'
    """
    task_id = self.request.id or "direct"
    logger.info(f"[Task {task_id}] Starting job processing for ID={job_id}")

    with get_sync_db() as session:
        job = session.query(JobDescription).filter(JobDescription.id == job_id).first()
        if not job:
            import time
            time.sleep(0.3)
            job = session.query(JobDescription).filter(JobDescription.id == job_id).first()

        if not job:
            logger.error(f"[Task {task_id}] Job ID={job_id} not found in database")
            return {"status": "not_found", "job_id": job_id}


        # Step 1: Mark processing
        job.status = "processing"
        job.task_id = task_id
        session.flush()

        self.update_state(
            state="PROCESSING",
            meta={
                "progress": 25,
                "step": "Extracting skills",
                "job_id": job_id,
            },
        )

        try:
            # Step 2: Extract skills if not present
            if not job.parsed_skills:
                logger.info(f"[Task {task_id}] Extracting skills for job ID={job_id}...")
                skills = extract_skills(job.raw_text)
                job.parsed_skills = skills
                session.flush()

            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": 55,
                    "step": "Generating embeddings",
                    "job_id": job_id,
                },
            )

            # Step 3: Generate embedding vector
            logger.info(f"[Task {task_id}] Generating vector embedding for job ID={job_id}...")
            embedding = generate_embedding(job.raw_text)
            job.embedding = embedding

            # Step 4: Mark completed
            job.status = "completed"
            session.flush()

            logger.info(
                f"[Task {task_id}] ✅ Job ID={job_id} processed successfully: "
                f"{len(job.parsed_skills or [])} skills, {len(embedding)} dim vector"
            )

            return {
                "status": "completed",
                "job_id": job_id,
                "task_id": task_id,
                "skills_count": len(job.parsed_skills or []),
                "embedding_dims": len(embedding),
            }

        except Exception as e:
            logger.exception(f"[Task {task_id}] ❌ Failed processing job ID={job_id}: {e}")
            job.status = "failed"
            session.flush()
            raise


@shared_task(name="app.tasks.embedding_tasks.generate_text_embedding_task")
def generate_text_embedding_task(text: str) -> list[float]:
    """Generate vector embedding for arbitrary text asynchronously."""
    return generate_embedding(text)


@shared_task(bind=True, name="app.tasks.embedding_tasks.batch_process_embeddings_task")
def batch_process_embeddings_task(self, item_type: str, item_ids: list[int]) -> dict:
    """Batch embed multiple resumes or job descriptions in the background.

    Args:
        item_type: 'resume' or 'job'
        item_ids: List of database IDs to embed
    """
    total = len(item_ids)
    processed = 0
    results = {}

    with get_sync_db() as session:
        for idx, item_id in enumerate(item_ids):
            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": int((idx / total) * 100),
                    "current_index": idx,
                    "total": total,
                    "current_id": item_id,
                },
            )
            try:
                if item_type == "resume":
                    record = session.query(Resume).filter(Resume.id == item_id).first()
                else:
                    record = session.query(JobDescription).filter(JobDescription.id == item_id).first()

                if record:
                    if record.embedding is None:
                        record.embedding = generate_embedding(record.raw_text)
                        record.status = "completed"
                        session.flush()
                        results[item_id] = "embedded"
                    else:
                        results[item_id] = "already_embedded"
                    processed += 1
                else:
                    results[item_id] = "not_found"
            except Exception as e:
                logger.error(f"Error processing {item_type} {item_id}: {e}")
                results[item_id] = f"error: {e}"

    return {
        "status": "completed",
        "item_type": item_type,
        "total": total,
        "processed": processed,
        "results": results,
    }
