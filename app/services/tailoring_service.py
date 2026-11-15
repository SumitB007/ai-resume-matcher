"""One-click tailoring (Phase 15, roadmap §9.2).

Scores a builder document against a job with the *same math as the matcher*
(0.6 semantic + 0.4 keyword, same embedding model, same dictionary) and
assembles per-change suggestions. Nothing here mutates the document —
suggestions are proposals the UI accepts or rejects one by one, and the
client applies accepted ones to a duplicate. The no-fabrication guardrail
is structural: add-skill suggestions come from the dictionary diff, bullet
rewrites go through the existing rewriter (which rephrases the user's own
facts), and the summary variant is generated from the document's own title
and skills.
"""

import re

from app.services.embedding_service import compute_cosine_similarity, generate_embedding
from app.services.keyword_service import (
    category_for_skill,
    compute_keyword_overlap,
    extract_skills,
    find_missing_keywords,
)
from app.services.llm_service import (
    _numbers_guard,
    generate_summary_variants,
    rewrite_bullet_point,
)

_WEAK_PREFIXES = ("responsible for", "worked on", "helped", "tasked with", "duties included")


def score_texts(resume_text: str, job_text: str) -> dict:
    """Matcher-identical scoring for arbitrary texts (no DB rows needed)."""
    similarity = compute_cosine_similarity(
        generate_embedding(resume_text), generate_embedding(job_text)
    )
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    keyword = compute_keyword_overlap(resume_skills, job_skills)
    similarity_pct = round(max(0.0, min(1.0, similarity)) * 100, 2)
    keyword_pct = round(keyword * 100, 2)
    return {
        "overall_score": round(0.6 * similarity_pct + 0.4 * keyword_pct, 2),
        "similarity_score": similarity_pct,
        "keyword_score": keyword_pct,
        "matched_keywords": sorted(set(resume_skills) & set(job_skills)),
        "missing_keywords": find_missing_keywords(resume_skills, job_skills),
    }


def find_weak_bullets(content: dict, limit: int = 4) -> list[dict]:
    """Bullets most worth rewriting: no metric and either short or opened
    with a weak passive prefix. Deterministic, most-recent roles first."""
    weak: list[dict] = []
    for exp_idx, entry in enumerate(content.get("experience") or []):
        for bullet_idx, bullet in enumerate(entry.get("bullets") or []):
            text = (bullet or "").strip()
            if len(text) < 15:
                continue
            has_metric = bool(re.search(r"\d", text))
            weak_opener = text.lower().startswith(_WEAK_PREFIXES)
            if not has_metric and (weak_opener or len(text) < 110):
                weak.append(
                    {
                        "experience_index": exp_idx,
                        "bullet_index": bullet_idx,
                        "original": text,
                        "weak_opener": weak_opener,
                    }
                )
    return weak[:limit]


def _extract_single_bullet(text: str) -> str | None:
    """Reduce rewriter output to one drop-in bullet, or None.

    The rewriter (LLM or its offline fallback) often answers with a small
    document — headers, multiple variations, rationale. A tailor suggestion
    must be a single bullet the user can accept as-is, so: prefer the first
    bulleted line; accept a lone plain paragraph; reject anything else.
    """
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines:
        if ln.startswith(("•", "- ")):
            candidate = ln.lstrip("•- ").strip().strip("*")
            if 25 <= len(candidate) <= 260 and "#" not in candidate:
                return candidate
    if lines and all("#" not in ln and not ln.startswith("**") for ln in lines):
        joined = " ".join(lines)
        if 25 <= len(joined) <= 260:
            return joined
    return None


async def build_suggestions(
    content: dict,
    missing_keywords: list[str],
    job_text: str,
    job_title: str,
    model: str | None = None,
) -> dict:
    """Assemble the suggestion list. Returns suggestions + generation meta."""
    suggestions: list[dict] = []
    models_used: list[str] = []
    any_fallback = False

    for i, skill in enumerate(missing_keywords[:12]):
        suggestions.append(
            {
                "id": f"skill-{i}",
                "type": "add_skill",
                "skill": skill,
                "group": category_for_skill(skill),
                "original": "",
                "proposed": skill,
            }
        )

    # Numbers anywhere in the document are the user's own facts; a rewrite
    # may reuse them but never introduce new ones (§15.7).
    document_numbers_text = " ".join(
        [content.get("summary") or ""]
        + [
            bullet
            for entry in content.get("experience") or []
            for bullet in entry.get("bullets") or []
        ]
    )
    for j, weak in enumerate(find_weak_bullets(content)):
        result = await rewrite_bullet_point(
            bullet_point=weak["original"],
            job_context=job_text[:600],
            missing_skills=missing_keywords,
            model=model,
        )
        models_used.append(result["model_used"])
        any_fallback = any_fallback or result["fallback_used"]
        rewritten = _extract_single_bullet(result["rewrite_content"] or "")
        if rewritten:
            guarded = _numbers_guard(
                [rewritten], f"{weak['original']} {document_numbers_text}"
            )
            rewritten = guarded[0] if guarded else None
        if rewritten and rewritten != weak["original"]:
            suggestions.append(
                {
                    "id": f"bullet-{j}",
                    "type": "rewrite_bullet",
                    "experience_index": weak["experience_index"],
                    "bullet_index": weak["bullet_index"],
                    "original": weak["original"],
                    "proposed": rewritten,
                }
            )

    personal = content.get("personal") or {}
    doc_skills = [
        skill
        for group in (content.get("skills") or {}).get("groups", [])
        for skill in group.get("skills", [])
    ]
    summary = await generate_summary_variants(
        title=personal.get("title", ""),
        years="",
        skills=doc_skills[:8],
        target_role=job_title,
        model=model,
    )
    models_used.append(summary["model_used"])
    any_fallback = any_fallback or summary["fallback_used"]
    if summary["variants"]:
        proposed_summary = summary["variants"][0]["text"]
        if proposed_summary != (content.get("summary") or ""):
            suggestions.append(
                {
                    "id": "summary-0",
                    "type": "summary",
                    "original": content.get("summary") or "",
                    "proposed": proposed_summary,
                }
            )

    return {
        "suggestions": suggestions,
        "model_used": models_used[0] if models_used else "",
        "fallback_used": any_fallback,
    }
