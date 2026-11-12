"""Unit tests for PDF Match Report Generation (Phase 10)."""

import pytest
from app.database import get_sync_db
from app.models.resume import Resume
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.services.pdf_export_service import generate_match_report_pdf


def test_generate_match_report_pdf(test_user_id, sample_resume_text, sample_job_description):
    """Test generating a styled PDF assessment report for a match result."""
    with get_sync_db() as session:
        resume = Resume(
            user_id=test_user_id,
            raw_text=sample_resume_text,
            file_name="jane_doe_backend.pdf",
            parsed_skills=["python", "fastapi", "postgresql", "redis", "docker"],
            status="completed",
        )
        session.add(resume)
        session.flush()

        job = JobDescription(
            user_id=test_user_id,
            raw_text=sample_job_description,
            title="Principal Backend Engineer",
            company="Stripe Global",
            parsed_skills=["python", "fastapi", "postgresql", "kubernetes", "kafka"],
            status="completed",
        )
        session.add(job)
        session.flush()

        match = MatchResult(
            resume_id=resume.id,
            job_id=job.id,
            user_id=test_user_id,
            overall_score=82.5,
            similarity_score=78.0,
            keyword_score=87.0,
            section_scores={
                "skills_match": 87.0,
                "experience_relevance": 82.5,
                "keyword_density": 78.0,
            },
            missing_keywords=["kubernetes", "kafka"],
            ai_feedback=(
                "### 1. Strengths & Alignments\n"
                "• **Core Technical Fit**: Strong background in Python and FastAPI microservices.\n"
                "### 2. Strategic Improvement Areas\n"
                "• **Distributed Systems**: Incorporate streaming/queue architectures like Kafka into your bullets.\n"
                "• **Cloud Orchestration**: Quantify container deployment metrics with Kubernetes."
            ),
        )
        session.add(match)
        session.flush()

        pdf_bytes = generate_match_report_pdf(match, resume, job)

        # 1. Assert PDF magic bytes header
        assert pdf_bytes.startswith(b"%PDF-"), "Generated file does not have valid PDF magic bytes"

        # 2. Assert reasonable file size
        assert len(pdf_bytes) > 2000, f"PDF file size too small: {len(pdf_bytes)} bytes"

        # 3. Assert EOF marker
        assert b"%%EOF" in pdf_bytes or b"trailer" in pdf_bytes
