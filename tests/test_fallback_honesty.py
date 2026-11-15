"""Option B fallback tests (2026-11-15): the offline fallback may only use
facts from the user's own prompt, with [add your metric] placeholders where
a number would go. Invented metrics are pinned as absent by name.
"""

import re

from app.services.llm_service import _generate_local_fallback

INVENTED = ["42%", "99.98", "15,000", "65%", "3x", "80%", "350ms", "45ms", "5+ microservices"]


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?%?", text))


def _assert_no_invention(output: str, prompt: str, formatting: set[str] = {"1", "2", "3", "4"}):
    for bad in INVENTED:
        assert bad not in output, f"invented metric present: {bad}"
    assert _numbers(output) <= _numbers(prompt) | formatting


REWRITE_PROMPT = (
    'ORIGINAL BULLET POINT:\n"Responsible for building REST APIs"\n\n'
    "TARGET SKILLS TO INTEGRATE IF POSSIBLE: kubernetes\n"
    "TARGET JOB CONTEXT:\nSenior Backend Developer role\n\n"
    "Rewrite this bullet point into 2 variations:"
)


def test_rewrite_fallback_uses_own_bullet_with_placeholders():
    out = _generate_local_fallback(REWRITE_PROMPT)
    assert "Built REST APIs" in out  # the user's own bullet, verb-first
    assert "[add your metric" in out
    _assert_no_invention(out, REWRITE_PROMPT)


def test_rewrite_fallback_preserves_users_own_number():
    prompt = REWRITE_PROMPT.replace(
        "building REST APIs", "building REST APIs serving 2M requests per day"
    )
    out = _generate_local_fallback(prompt)
    assert "2M" in out or "2" in _numbers(out)
    _assert_no_invention(out, prompt)


FEEDBACK_PROMPT = (
    "RESUME SNIPPET:\nJane Developer\nSkills: Python, FastAPI, PostgreSQL\n"
    "- Built a FastAPI platform serving real traffic\n\n"
    "JOB DESCRIPTION:\nSenior Backend Developer. Must know Python, FastAPI, PostgreSQL, Kubernetes.\n\n"
    "OVERALL MATCH SCORE: 81.66%\n"
    'SECTION SCORES:\n{"skills_match": 90.91}\n'
    "MISSING SKILLS / KEYWORD GAPS: kubernetes, kafka\n\n"
    "Please provide detailed feedback"
)


def test_feedback_fallback_uses_real_match_data():
    out = _generate_local_fallback(FEEDBACK_PROMPT)
    assert "81.66" in out  # the user's real score
    assert "kubernetes" in out and "kafka" in out  # real gaps
    assert "python" in out.lower()  # real matched skill
    assert "[add your metric" in out
    assert "Built a FastAPI platform" in out  # their own bullet, rephrased
    _assert_no_invention(out, FEEDBACK_PROMPT)


def test_generic_fallback_is_an_honest_template():
    out = _generate_local_fallback("Write something about my career")
    assert "[add your metric]" in out
    _assert_no_invention(out, "Write something about my career")
