"""Unit tests for Resume Version Progress and ATS Analytics (Phase 9)."""

import pytest
from datetime import datetime, timezone
from app.database import get_sync_db, async_session_factory
from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.services.analytics_service import (
    get_resume_progress_for_job,
    get_resume_evaluations_summary,
    get_user_analytics_dashboard,
)


@pytest.mark.asyncio
async def test_resume_version_progress(test_user_id):
    """Test score progression and skill acquisition tracking across resume versions for the same job."""
    with get_sync_db() as session:
        # Create a target job
        job = JobDescription(
            user_id=test_user_id,
            raw_text="Lead Cloud Platform Engineer with Kubernetes, Terraform, Go, and GraphQL experience.",
            title="Lead Cloud Platform Engineer",
            company="CloudScale",
            status="completed",
        )
        session.add(job)
        session.flush()

        # Create Resume v1 (junior, missing multiple keywords)
        resume_v1 = Resume(
            user_id=test_user_id,
            raw_text="Junior Engineer familiar with Go and Docker.",
            file_name="resume_v1.pdf",
            status="completed",
        )
        session.add(resume_v1)
        session.flush()

        match_v1 = MatchResult(
            resume_id=resume_v1.id,
            job_id=job.id,
            user_id=test_user_id,
            overall_score=60.0,
            similarity_score=55.0,
            keyword_score=67.5,
            missing_keywords=["kubernetes", "terraform", "graphql"],
            created_at=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
        session.add(match_v1)

        # Create Resume v2 (tailored, acquired Kubernetes and Terraform)
        resume_v2 = Resume(
            user_id=test_user_id,
            raw_text="Cloud Engineer with Kubernetes, Terraform, Docker, and Go production deployments.",
            file_name="resume_v2.pdf",
            status="completed",
        )
        session.add(resume_v2)
        session.flush()

        match_v2 = MatchResult(
            resume_id=resume_v2.id,
            job_id=job.id,
            user_id=test_user_id,
            overall_score=85.0,
            similarity_score=82.0,
            keyword_score=89.5,
            missing_keywords=["graphql"],
            created_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
        )
        session.add(match_v2)
        session.flush()

        job_id = job.id
        resume_v2_id = resume_v2.id

    # Test progress tracking
    async with async_session_factory() as async_session:
        progress = await get_resume_progress_for_job(
            job_id=job_id,
            user_id=test_user_id,
            db=async_session,
        )

        assert progress.job_id == job_id
        assert progress.total_evaluations == 2
        assert progress.initial_score == 60.0
        assert progress.latest_score == 85.0
        assert progress.score_improvement == 25.0
        assert progress.average_score == 72.5

        # Check skills gained
        assert "kubernetes" in progress.skills_gained
        assert "terraform" in progress.skills_gained
        assert "graphql" not in progress.skills_gained

        # Check timeline length
        assert len(progress.timeline) == 2
        assert progress.timeline[0].overall_score == 60.0
        assert progress.timeline[1].overall_score == 85.0


@pytest.mark.asyncio
async def test_user_analytics_dashboard(test_user_id):
    """Test comprehensive dashboard aggregates metrics and skill gap frequencies."""
    async with async_session_factory() as async_session:
        dashboard = await get_user_analytics_dashboard(
            user_id=test_user_id,
            db=async_session,
        )

        assert dashboard.total_resumes >= 2
        assert dashboard.total_jobs >= 1
        assert dashboard.total_matches >= 2
        assert dashboard.average_match_score is not None
        assert dashboard.highest_match_score is not None

        # Verify top missing skills list
        top_missing_names = [item.skill for item in dashboard.top_missing_skills]
        assert "graphql" in top_missing_names

        # Verify recent matches returned
        assert len(dashboard.recent_matches) > 0
