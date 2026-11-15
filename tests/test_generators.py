"""Unit tests for the Phase 15 generators' offline paths + guardrails.

The load-bearing test is the fabrication guard: generated bullets may only
contain numbers the user supplied. Everything else pins shapes the
frontend depends on.
"""

import re

import pytest

from app.config import settings
from app.services.keyword_service import group_skills_by_category
from app.services.llm_service import (
    _fallback_bullets,
    _numbers_guard,
    generate_bullets,
    generate_resume_draft,
    generate_summary_variants,
    suggest_skill_groups,
)
from app.services.tailoring_service import find_weak_bullets

NOTES = (
    "I was responsible for the payments API; "
    "worked on database migration to postgres; "
    "helped reduce deploy time from 40 minutes to 15 minutes"
)


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?%?", text))


def test_fallback_bullets_rephrase_without_inventing():
    bullets = _fallback_bullets(NOTES)
    assert len(bullets) == 3
    assert bullets[0].startswith("Owned")
    assert bullets[1].startswith("Developed")
    for bullet in bullets:
        assert _numbers(bullet) <= _numbers(NOTES)
    assert "40 minutes to 15 minutes" in " ".join(bullets)


def test_numbers_guard_drops_invented_metrics():
    items = ["Improved latency by 40%", "Built the API used by the team"]
    assert _numbers_guard(items, "built the api for the team") == [
        "Built the API used by the team"
    ]
    assert _numbers_guard(items, "improved latency by 40% last year") == items


@pytest.mark.asyncio
async def test_generate_bullets_without_key_uses_fallback(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    result = await generate_bullets(role="Backend Developer", company="Acme", notes=NOTES)
    assert result["fallback_used"] is True
    assert len(result["bullets"]) == 3


@pytest.mark.asyncio
async def test_summary_variants_without_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    result = await generate_summary_variants(
        title="Senior Backend Developer",
        years="6 years",
        skills=["python", "fastapi"],
        target_role="Staff Engineer",
    )
    assert result["fallback_used"] is True
    labels = [v["label"] for v in result["variants"]]
    assert labels == ["Professional", "Impact-led", "Concise"]
    assert "python" in result["variants"][0]["text"].lower()


def test_skill_grouping_is_deterministic():
    groups = group_skills_by_category(["python", "kubernetes", "postgresql", "mentoring", "cobol"])
    by_name = {g["name"]: g["skills"] for g in groups}
    assert by_name["Languages"] == ["python"]
    assert by_name["Cloud & DevOps"] == ["kubernetes"]
    assert by_name["Databases & Storage"] == ["postgresql"]
    assert by_name["Other"] == ["cobol"]
    # Display order: Languages before Cloud & DevOps before Other
    names = [g["name"] for g in groups]
    assert names == sorted(names, key=["Languages", "Frameworks & Libraries", "Databases & Storage", "Cloud & DevOps", "Data & AI", "Practices & Tools", "Other"].index)


@pytest.mark.asyncio
async def test_suggest_skill_groups_without_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    result = await suggest_skill_groups(
        text="We need a Python developer with FastAPI, PostgreSQL and Docker experience."
    )
    all_skills = [s for g in result["groups"] for s in g["skills"]]
    assert "python" in all_skills and "docker" in all_skills


@pytest.mark.asyncio
async def test_resume_draft_shape_without_key(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", None)
    result = await generate_resume_draft(
        title="Data Engineer", level="senior", skills_text="python, sql, airflow, dbt"
    )
    content = result["content"]
    assert content["personal"]["title"] == "Data Engineer"
    assert content["summary"]
    assert content["experience"][0]["role"] == "Data Engineer"
    assert content["experience"][0]["bullets"] == []  # skeleton, not fabricated history
    grouped = [s for g in content["skills"]["groups"] for s in g["items"]]
    assert "airflow" in grouped


def test_find_weak_bullets():
    content = {
        "experience": [
            {
                "role": "Dev",
                "bullets": [
                    "Responsible for the API layer",  # weak opener, no metric
                    "Cut p95 latency from 900ms to 210ms across 14 services by adding Redis caching and query tuning",  # strong
                    "Did testing",  # too short to judge (<15 chars after strip? 'Did testing' is 11) -> skipped
                    "Maintained internal dashboards and reports for the ops team",  # no metric, medium length
                ],
            }
        ]
    }
    weak = find_weak_bullets(content)
    originals = [w["original"] for w in weak]
    assert "Responsible for the API layer" in originals
    assert "Maintained internal dashboards and reports for the ops team" in originals
    assert all("900ms" not in o for o in originals)


def test_extract_single_bullet():
    from app.services.tailoring_service import _extract_single_bullet

    doc_style = (
        "### Recommended Rewrites\n\n"
        "**Variation 1 — Strong & Quantified:**\n"
        "• Spearheaded the re-architecture of core backend services using FastAPI.\n\n"
        "**Variation 2:**\n• Something else entirely here for the second variation."
    )
    assert _extract_single_bullet(doc_style) == (
        "Spearheaded the re-architecture of core backend services using FastAPI."
    )
    assert _extract_single_bullet("Built REST APIs for the payments platform") == (
        "Built REST APIs for the payments platform"
    )
    assert _extract_single_bullet("### Only a header\n**and bold**") is None
    assert _extract_single_bullet("too short") is None
