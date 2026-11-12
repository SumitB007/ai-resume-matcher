"""LLM background tasks — asynchronous AI feedback generation via Celery."""

import asyncio
import logging
from celery import shared_task

from app.database import get_sync_db
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.job import JobDescription
from app.services.llm_service import generate_match_feedback

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.tasks.llm_tasks.generate_match_feedback_task")
def generate_match_feedback_task(
    self, match_id: int, model: str | None = None
) -> dict:
    """Background task to generate AI feedback and recommendations for a match result.

    Updates the match_results table with the generated ai_feedback text.
    """
    task_id = self.request.id or "direct"
    logger.info(f"[Task {task_id}] Generating AI feedback for Match ID={match_id}")

    with get_sync_db() as session:
        match_record = session.query(MatchResult).filter(MatchResult.id == match_id).first()
        if not match_record:
            logger.error(f"[Task {task_id}] Match ID={match_id} not found")
            return {"status": "not_found", "match_id": match_id}

        resume = session.query(Resume).filter(Resume.id == match_record.resume_id).first()
        job = session.query(JobDescription).filter(JobDescription.id == match_record.job_id).first()

        if not resume or not job:
            logger.error(f"[Task {task_id}] Associated resume or job not found for Match {match_id}")
            return {"status": "missing_dependencies", "match_id": match_id}

        self.update_state(
            state="PROCESSING",
            meta={"progress": 30, "step": "Calling LLM pipeline", "match_id": match_id},
        )

        try:
            # Run async LLM service within synchronous Celery task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            feedback_data = loop.run_until_complete(
                generate_match_feedback(
                    resume_text=resume.raw_text,
                    job_text=job.raw_text,
                    missing_keywords=match_record.missing_keywords,
                    section_scores=match_record.section_scores,
                    overall_score=match_record.overall_score,
                    model=model,
                )
            )
            loop.close()

            feedback_text = feedback_data.get("feedback_text", "")
            match_record.ai_feedback = feedback_text
            session.flush()

            logger.info(f"[Task {task_id}] ✅ AI feedback generated for Match ID={match_id}")
            return {
                "status": "completed",
                "match_id": match_id,
                "model_used": feedback_data.get("model_used"),
                "fallback_used": feedback_data.get("fallback_used"),
                "feedback_length": len(feedback_text),
            }

        except Exception as e:
            logger.exception(f"[Task {task_id}] ❌ Failed generating AI feedback for Match {match_id}: {e}")
            raise
