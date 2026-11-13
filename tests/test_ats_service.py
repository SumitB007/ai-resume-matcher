"""Unit tests for the standalone ATS checker (app/services/ats_service.py).

The service is pure (text in, result out), so these tests need no database,
no Redis, and no network — they pin the checker's contract: 22 checks in 6
groups, a strong resume scoring clearly above a weak one, and specific rules
firing on specific defects.
"""

from app.services.ats_service import run_ats_checks

STRONG_RESUME = """Jane Developer
jane.developer@example.com | +1 555-123-4567 | linkedin.com/in/janedev | github.com/janedev

Summary
Senior backend developer with 6 years of experience building Python APIs and data pipelines for SaaS products.

Experience
Senior Backend Developer — TechCorp (2021 - Present)
• Built a FastAPI microservice platform serving 2M requests per day with PostgreSQL and Redis
• Reduced API latency by 45% by introducing Redis caching and query optimization
• Led migration of legacy Django monolith to containerized services on Kubernetes
• Automated CI/CD pipelines with GitHub Actions, cutting deploy time from 40 minutes to 8 minutes
• Mentored 4 junior developers and drove code review standards across the team
• Designed REST APIs consumed by 3 frontend teams, documented with OpenAPI

Backend Developer — DataWorks (2019 - 2021)
• Developed data ingestion pipelines processing 500K records daily using Python and Kafka
• Improved test coverage from 52% to 91% by introducing pytest fixtures and factories
• Shipped a reporting service that saved analysts 10 hours per week

Skills
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, Kafka, AWS, pytest, Git, REST APIs

Education
B.Tech, Computer Science — State University (2015 - 2019)
"""

WEAK_RESUME = """John Smith

Objective: I am looking for a job where I can use my skills and I am a hard worker and I am a team player.

Worked at a company for some time doing various tasks and helping with projects.
Responsible for many things including coding and meetings and other duties as assigned.
Also worked at another place before that.
"""


def _check(result, check_id):
    return next(c for c in result["checks"] if c["id"] == check_id)


def test_check_inventory_is_22_in_6_groups():
    result = run_ats_checks(STRONG_RESUME)
    assert len(result["checks"]) == 22
    assert set(result["groups"].keys()) == {
        "file_parse", "contact", "sections", "content", "skills", "length_format",
    }
    ids = [c["id"] for c in result["checks"]]
    assert len(set(ids)) == 22  # stable, unique ids


def test_strong_resume_scores_high():
    result = run_ats_checks(STRONG_RESUME)
    assert result["score"] >= 80
    assert _check(result, "email_present")["status"] == "pass"
    assert _check(result, "has_experience")["status"] == "pass"
    assert _check(result, "skills_detected")["status"] == "pass"
    assert result["word_count"] > 150


def test_weak_resume_scores_low():
    result = run_ats_checks(WEAK_RESUME)
    assert result["score"] < 50
    assert _check(result, "email_present")["status"] == "fail"
    assert _check(result, "bullet_count")["status"] in ("warn", "fail")
    assert _check(result, "quantified_bullets")["status"] == "fail"


def test_score_within_bounds_and_deterministic():
    first = run_ats_checks(STRONG_RESUME)
    second = run_ats_checks(STRONG_RESUME)
    assert 0 <= first["score"] <= 100
    assert first == second  # rule-based: same input, same output, always


def test_empty_text_does_not_crash():
    result = run_ats_checks("")
    assert result["score"] >= 0
    assert _check(result, "email_present")["status"] == "fail"
