"""Tests for Phase 8: LLM Features (OpenRouter integration, feedback, rewrites, and streaming)."""

import pytest
from app.services.llm_service import (
    call_openrouter,
    stream_openrouter,
    generate_match_feedback,
    rewrite_bullet_point,
    extract_skills_llm,
)
from app.database import get_sync_db
from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.tasks.llm_tasks import generate_match_feedback_task


@pytest.mark.asyncio
async def test_call_openrouter_basic():
    """Test calling openrouter completion logic."""
    res = await call_openrouter(
        prompt="Explain the importance of quantified metrics in technical resumes in two sentences.",
        system_prompt="You are a professional resume advisor.",
    )
    assert res is not None
    assert "content" in res
    assert len(res["content"]) > 20
    assert "model_used" in res
    assert "usage" in res


@pytest.mark.asyncio
async def test_generate_match_feedback(sample_resume_text, sample_job_description):
    """Test generating full structured match feedback."""
    missing_keywords = ["kubernetes", "terraform", "kafka"]
    section_scores = {
        "skills_match": 75.0,
        "experience_relevance": 80.0,
        "keyword_density": 70.0,
    }

    result = await generate_match_feedback(
        resume_text=sample_resume_text,
        job_text=sample_job_description,
        missing_keywords=missing_keywords,
        section_scores=section_scores,
        overall_score=76.5,
    )

    assert result is not None
    assert "feedback_text" in result
    feedback = result["feedback_text"]
    assert len(feedback) > 100
    # Verify core sections are present
    assert "Strengths" in feedback or "Alignments" in feedback or "###" in feedback
    assert "Rewrites" in feedback or "Formula" in feedback or "Bullet" in feedback


@pytest.mark.asyncio
async def test_rewrite_bullet_point():
    """Test rewriting a weak bullet into a quantified, strong bullet."""
    weak_bullet = "Worked on backend Python APIs and database queries."
    result = await rewrite_bullet_point(
        bullet_point=weak_bullet,
        job_context="Senior Backend Developer required to optimize high-scale FastAPI services.",
        missing_skills=["FastAPI", "Redis", "PostgreSQL"],
    )

    assert result is not None
    assert result["original_bullet"] == weak_bullet
    assert "rewrite_content" in result
    assert len(result["rewrite_content"]) > len(weak_bullet)
    assert "model_used" in result


@pytest.mark.asyncio
async def test_extract_skills_llm():
    """Test LLM-based technical skill extraction."""
    text = (
        "We are looking for a Senior Engineer experienced in Go, Kubernetes, "
        "PostgreSQL, Prometheus, Kafka, and Google Cloud Platform (GCP)."
    )
    result = await extract_skills_llm(text=text)

    assert result is not None
    assert "skills" in result
    skills = result["skills"]
    assert isinstance(skills, list)
    assert len(skills) > 0
    # Check that known technologies were captured
    assert any("postgresql" in s or "kubernetes" in s or "kafka" in s for s in skills)


@pytest.mark.asyncio
async def test_stream_openrouter():
    """Test streaming completion token-by-token."""
    tokens = []
    async for token in stream_openrouter(
        prompt="State three core virtues of a high-performance distributed backend."
    ):
        tokens.append(token)

    assert len(tokens) > 5
    full_text = "".join(tokens)
    assert len(full_text) > 20


def test_generate_match_feedback_task(sample_resume_text, sample_job_description, test_user_id):
    """Test Celery background task for generating AI feedback."""
    with get_sync_db() as session:
        resume = Resume(
            user_id=test_user_id,
            raw_text=sample_resume_text,
            status="completed",
        )
        job = JobDescription(
            user_id=test_user_id,
            raw_text=sample_job_description,
            status="completed",
        )
        session.add_all([resume, job])
        session.flush()

        match_record = MatchResult(
            resume_id=resume.id,
            job_id=job.id,
            user_id=test_user_id,
            similarity_score=82.0,
            keyword_score=75.0,
            overall_score=79.2,
            section_scores={"skills_match": 80.0},
            missing_keywords=["kubernetes", "kafka"],
            ai_feedback=None,
        )
        session.add(match_record)
        session.flush()
        match_id = match_record.id

    # Execute task in-process
    task_res = generate_match_feedback_task.apply(args=[match_id])

    assert task_res.state == "SUCCESS"
    assert task_res.result["status"] == "completed"
    assert task_res.result["match_id"] == match_id
    assert task_res.result["feedback_length"] > 50

    # Verify database was updated
    with get_sync_db() as session:
        updated = session.query(MatchResult).filter(MatchResult.id == match_id).first()
        assert updated is not None
        assert updated.ai_feedback is not None
        assert len(updated.ai_feedback) > 50
