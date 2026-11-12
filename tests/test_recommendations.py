"""Unit tests for Job Recommendations (Phase 9)."""

import pytest
from app.database import get_sync_db
from app.models.resume import Resume
from app.models.job import JobDescription
from app.services.embedding_service import generate_embedding
from app.services.keyword_service import extract_skills
from app.services.recommendation_service import get_job_recommendations_for_resume


@pytest.mark.asyncio
async def test_job_recommendations(test_user_id, sample_resume_text, sample_job_description):
    """Test pgvector nearest-neighbor search ranks relevant jobs at the top."""
    # 1. Create a resume in DB with embedding and skills
    resume_emb = generate_embedding(sample_resume_text)
    resume_skills = extract_skills(sample_resume_text)

    with get_sync_db() as session:
        resume = Resume(
            user_id=test_user_id,
            raw_text=sample_resume_text,
            file_name="recommendation_test_resume.pdf",
            embedding=resume_emb,
            parsed_skills=resume_skills,
            status="completed",
        )
        session.add(resume)
        session.flush()
        resume_id = resume.id

        # 2. Create 2 distinct jobs: one highly relevant backend job, one irrelevant design job
        job_emb_1 = generate_embedding(sample_job_description)
        job_skills_1 = extract_skills(sample_job_description)
        job_1 = JobDescription(
            user_id=test_user_id,
            raw_text=sample_job_description,
            title="Senior Python Backend Architect",
            company="TechCorp Cloud",
            embedding=job_emb_1,
            parsed_skills=job_skills_1,
            status="completed",
        )
        session.add(job_1)

        irrelevant_job_text = (
            "UI/UX Visual Designer required. Must be proficient in Figma, Adobe XD, Photoshop, "
            "typography, design systems, and wireframing."
        )
        job_emb_2 = generate_embedding(irrelevant_job_text)
        job_skills_2 = extract_skills(irrelevant_job_text)
        job_2 = JobDescription(
            user_id=test_user_id,
            raw_text=irrelevant_job_text,
            title="Senior UI/UX Designer",
            company="Creative Studios",
            embedding=job_emb_2,
            parsed_skills=job_skills_2,
            status="completed",
        )
        session.add(job_2)
        session.flush()

    # 3. Call recommendation service
    from app.database import async_session_factory

    async with async_session_factory() as async_session:
        resp = await get_job_recommendations_for_resume(
            resume_id=resume_id,
            current_user_id=test_user_id,
            db=async_session,
            limit=5,
            include_all_jobs=True,
        )

        assert resp.resume_id == resume_id
        assert len(resp.recommendations) >= 2

        # The python backend job MUST rank ahead of the UI/UX job
        top_rec = resp.recommendations[0]
        assert "Python" in top_rec.title or "Backend" in top_rec.title
        assert top_rec.similarity_score > 60.0
        assert top_rec.overall_score > 60.0
        assert "python" in top_rec.matching_skills
        assert len(top_rec.matching_skills) > 0


@pytest.mark.asyncio
async def test_recommendations_threshold_filter(test_user_id, sample_resume_text):
    """Test min_similarity parameter filters out low-matching jobs."""
    from app.database import async_session_factory

    with get_sync_db() as session:
        resume = session.query(Resume).filter(
            Resume.user_id == test_user_id,
            Resume.file_name == "recommendation_test_resume.pdf"
        ).first()
        assert resume is not None
        resume_id = resume.id

    async with async_session_factory() as async_session:
        # Request with a very high threshold (e.g. 95%) that irrelevant jobs cannot satisfy
        resp = await get_job_recommendations_for_resume(
            resume_id=resume_id,
            current_user_id=test_user_id,
            db=async_session,
            limit=10,
            min_similarity=90.0,
            include_all_jobs=True,
        )

        # UI/UX job should definitely not be in >= 90% results
        titles = [r.title for r in resp.recommendations]
        assert "Senior UI/UX Designer" not in titles
