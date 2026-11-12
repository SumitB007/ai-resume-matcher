"""Resume background tasks — parsing, skill extraction, and embedding generation."""

import logging
from celery import shared_task

from app.database import get_sync_db
from app.models.resume import Resume
from app.services.keyword_service import extract_skills
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.tasks.resume_tasks.process_resume_task")
def process_resume_task(self, resume_id: int) -> dict:
    """Background task to process an uploaded resume:

    1. Updates status to 'processing'
    2. Extracts skills from raw text (if not already extracted)
    3. Generates 384-dimensional vector embedding via Sentence-Transformers
    4. Updates database record with embedding, skills, and status 'completed'
    """
    task_id = self.request.id or "direct"
    logger.info(f"[Task {task_id}] Starting resume processing for ID={resume_id}")

    with get_sync_db() as session:
        resume = session.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            import time
            time.sleep(0.3)
            resume = session.query(Resume).filter(Resume.id == resume_id).first()

        if not resume:
            logger.error(f"[Task {task_id}] Resume ID={resume_id} not found in database")
            return {"status": "not_found", "resume_id": resume_id}


        # Step 1: Mark processing
        resume.status = "processing"
        resume.task_id = task_id
        session.flush()

        self.update_state(
            state="PROCESSING",
            meta={
                "progress": 25,
                "step": "Extracting skills",
                "resume_id": resume_id,
            },
        )

        try:
            # Step 2: Extract skills if not present
            if not resume.parsed_skills:
                logger.info(f"[Task {task_id}] Extracting skills for resume ID={resume_id}...")
                skills = extract_skills(resume.raw_text)
                resume.parsed_skills = skills
                session.flush()

            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": 55,
                    "step": "Generating embeddings",
                    "resume_id": resume_id,
                },
            )

            # Step 3: Generate embedding vector
            logger.info(f"[Task {task_id}] Generating vector embedding for resume ID={resume_id}...")
            embedding = generate_embedding(resume.raw_text)
            resume.embedding = embedding

            # Step 4: Mark completed
            resume.status = "completed"
            session.flush()

            logger.info(
                f"[Task {task_id}] ✅ Resume ID={resume_id} processed successfully: "
                f"{len(resume.parsed_skills or [])} skills, {len(embedding)} dim vector"
            )

            return {
                "status": "completed",
                "resume_id": resume_id,
                "task_id": task_id,
                "skills_count": len(resume.parsed_skills or []),
                "embedding_dims": len(embedding),
            }

        except Exception as e:
            logger.exception(f"[Task {task_id}] ❌ Failed processing resume ID={resume_id}: {e}")
            resume.status = "failed"
            session.flush()
            raise
