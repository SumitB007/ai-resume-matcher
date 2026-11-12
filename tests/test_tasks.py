"""Tests for Phase 7: Celery Background Tasks & Status Tracking."""

import pytest
from app.tasks.resume_tasks import process_resume_task
from app.tasks.embedding_tasks import (
    process_job_task,
    generate_text_embedding_task,
    batch_process_embeddings_task,
)
from app.database import get_sync_db
from app.models.resume import Resume
from app.models.job import JobDescription


def test_generate_text_embedding_task():
    """Test generating vector embedding asynchronously via Celery task."""
    text = "Senior Python Backend Developer with FastAPI and Redis experience."
    res = generate_text_embedding_task.apply(args=[text])

    assert res.state == "SUCCESS"
    vec = res.result
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)


def test_process_resume_task(sample_resume_text, test_user_id):
    """Test full resume background processing pipeline."""
    # Create a resume in pending state without embedding
    with get_sync_db() as session:
        resume = Resume(
            user_id=test_user_id,
            raw_text=sample_resume_text,
            file_name="test_worker_resume.pdf",
            status="pending",
        )
        session.add(resume)
        session.flush()
        resume_id = resume.id

    # Execute task in-process
    task_res = process_resume_task.apply(args=[resume_id])

    assert task_res.state == "SUCCESS"
    assert task_res.result["status"] == "completed"
    assert task_res.result["resume_id"] == resume_id
    assert task_res.result["embedding_dims"] == 384
    assert task_res.result["skills_count"] > 0

    # Verify database was updated
    with get_sync_db() as session:
        updated = session.query(Resume).filter(Resume.id == resume_id).first()
        assert updated is not None
        assert updated.status == "completed"
        assert updated.embedding is not None
        assert len(updated.embedding) == 384
        assert "python" in updated.parsed_skills or "fastapi" in updated.parsed_skills



def test_process_job_task(sample_job_description, test_user_id):
    """Test full job description background processing pipeline."""
    # Create a job in pending state without embedding
    with get_sync_db() as session:
        job = JobDescription(
            user_id=test_user_id,
            raw_text=sample_job_description,
            title="Senior Python Backend Developer",
            company="TechCorp Inc.",
            status="pending",
        )
        session.add(job)
        session.flush()
        job_id = job.id

    # Execute task in-process
    task_res = process_job_task.apply(args=[job_id])

    assert task_res.state == "SUCCESS"
    assert task_res.result["status"] == "completed"
    assert task_res.result["job_id"] == job_id
    assert task_res.result["embedding_dims"] == 384
    assert task_res.result["skills_count"] > 0

    # Verify database was updated
    with get_sync_db() as session:
        updated = session.query(JobDescription).filter(JobDescription.id == job_id).first()
        assert updated is not None
        assert updated.status == "completed"
        assert updated.embedding is not None
        assert len(updated.embedding) == 384


def test_batch_process_embeddings_task(sample_resume_text, test_user_id):
    """Test batch embedding generation task."""
    with get_sync_db() as session:
        r1 = Resume(user_id=test_user_id, raw_text=sample_resume_text, status="pending")
        r2 = Resume(user_id=test_user_id, raw_text=sample_resume_text, status="pending")
        session.add_all([r1, r2])
        session.flush()
        ids = [r1.id, r2.id]

    task_res = batch_process_embeddings_task.apply(args=["resume", ids])
    assert task_res.state == "SUCCESS"
    assert task_res.result["processed"] == 2
    assert task_res.result["results"][ids[0]] == "embedded"
    assert task_res.result["results"][ids[1]] == "embedded"

