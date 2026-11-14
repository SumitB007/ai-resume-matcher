"""Unit tests for the cover-letter generator's offline path (Phase 14).

The structured fallback is the guaranteed behaviour with no LLM key: a real,
specific letter built only from extracted facts. The honesty rule is pinned
by test: missing skills are framed as growth areas, never as experience.
"""

import pytest

from app.config import settings
from app.services.llm_service import _structured_fallback_letter, generate_cover_letter

RESUME_TEXT = """Jane Developer
Senior Backend Developer
jane@example.com

Summary
Senior backend developer with 6 years of experience building Python APIs.

Experience
Senior Backend Developer - TechCorp (2021 - Present)
- Built a FastAPI platform with PostgreSQL and Redis serving 2M requests per day

Skills
Python, FastAPI, PostgreSQL, Redis, Docker
"""

JOB_TEXT = (
    "Senior Backend Developer at Acme. Must know Python, FastAPI, PostgreSQL, "
    "Kubernetes and Kafka. Build REST APIs and microservices."
)


def _letter(tone="professional", missing=None):
    return _structured_fallback_letter(
        candidate_name="Jane Developer",
        candidate_title="Senior Backend Developer",
        years="6 years",
        matched_skills=["python", "fastapi", "postgresql"],
        missing_skills=missing if missing is not None else ["kubernetes", "kafka"],
        job_title="Senior Backend Developer",
        company="Acme",
        tone=tone,
    )


def test_fallback_letter_structure_and_facts():
    paragraphs = _letter()
    assert len(paragraphs) == 4
    joined = " ".join(paragraphs)
    assert "Senior Backend Developer" in paragraphs[0]
    assert "Acme" in paragraphs[0]
    assert "python" in joined.lower()
    assert "6 years" in joined


def test_missing_skills_are_honest_bridge_not_experience():
    joined = " ".join(_letter()).lower()
    assert "kubernetes" in joined
    assert "actively building depth" in joined  # growth framing
    assert "experience with kubernetes" not in joined
    assert "proficient in kubernetes" not in joined


def test_no_missing_skills_skips_bridge():
    joined = " ".join(_letter(missing=[])).lower()
    assert "actively building depth" not in joined


def test_tones_produce_different_letters():
    professional = " ".join(_letter("professional"))
    enthusiastic = " ".join(_letter("enthusiastic"))
    concise = " ".join(_letter("concise"))
    assert professional != enthusiastic != concise
    assert len(concise) < len(professional)


@pytest.mark.asyncio
async def test_generate_without_key_uses_structured_fallback(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    result = await generate_cover_letter(
        resume_text=RESUME_TEXT,
        job_text=JOB_TEXT,
        job_title="Senior Backend Developer",
        company="Acme",
    )
    assert result["fallback_used"] is True
    assert len(result["paragraphs"]) == 4
    assert "Acme" in result["paragraphs"][0]
