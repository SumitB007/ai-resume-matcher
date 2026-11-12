"""Keyword service — skill extraction, overlap scoring, and gap analysis.

Extracts skills from text using the curated skills dictionary,
computes keyword overlap between resume and job, and identifies gaps.
"""

import re
import logging

from app.utils.skills_dictionary import (
    ALL_SKILLS,
    PROGRAMMING_LANGUAGES,
    FRAMEWORKS,
    DATABASES,
    CLOUD_DEVOPS,
    DATA_ML,
    TOOLS_PRACTICES,
    SOFT_SKILLS,
)

logger = logging.getLogger(__name__)


def extract_skills(text: str) -> list[str]:
    """Extract known skills/keywords from text using the curated dictionary.

    Performs case-insensitive matching against the skills dictionary.
    Handles multi-word skills (e.g., "machine learning", "spring boot").

    Args:
        text: Raw text from a resume or job description.

    Returns:
        Sorted list of unique skills found in the text.
    """
    text_lower = text.lower()
    found_skills: set[str] = set()

    for skill in ALL_SKILLS:
        # Build a regex pattern that matches the skill as a whole word/phrase
        # Escape special regex characters in the skill name
        pattern = r"\b" + re.escape(skill) + r"\b"
        try:
            if re.search(pattern, text_lower):
                found_skills.add(skill)
        except re.error:
            # Some skill names might cause regex issues; fall back to simple contains
            if skill in text_lower:
                found_skills.add(skill)

    # Also match common abbreviations and variations
    _match_variations(text_lower, found_skills)

    return sorted(found_skills)


def _match_variations(text_lower: str, found_skills: set[str]) -> None:
    """Match common skill abbreviations and alternate spellings.

    Mutates `found_skills` in place.
    """
    variations = {
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "postgres": "postgresql",
        "k8s": "kubernetes",
        "tf": "terraform",
        "ci/cd": "ci/cd",
        "ml": "machine learning",
        "dl": "deep learning",
        "nlp": "natural language processing",
        "cv": "computer vision",
        "drf": "django",
        "rest": "rest api",
        "restful": "rest api",
        "react.js": "react",
        "reactjs": "react",
        "vue.js": "vue",
        "vuejs": "vue",
        "node": "node.js",
        "nodejs": "node.js",
        "express.js": "express",
        "expressjs": "express",
        "nestjs": "nest.js",
        "nextjs": "next.js",
        "nuxtjs": "nuxt.js",
        "mongo": "mongodb",
        "elastic": "elasticsearch",
        "gcp": "google cloud",
        "amazon web services": "aws",
        "github action": "github actions",
        "gitlab-ci": "gitlab ci",
    }

    for abbrev, canonical in variations.items():
        pattern = r"\b" + re.escape(abbrev) + r"\b"
        try:
            if re.search(pattern, text_lower) and canonical in ALL_SKILLS:
                found_skills.add(canonical)
        except re.error:
            if abbrev in text_lower and canonical in ALL_SKILLS:
                found_skills.add(canonical)


def compute_keyword_overlap(
    resume_skills: list[str],
    job_skills: list[str],
) -> float:
    """Compute what percentage of the job's required skills appear in the resume.

    This is the "ATS-style" literal keyword check.

    Args:
        resume_skills: Skills extracted from the resume.
        job_skills: Skills extracted from the job description.

    Returns:
        Overlap score between 0.0 and 1.0.
        Returns 1.0 if the job has no extractable skills.
    """
    if not job_skills:
        return 1.0

    resume_set = set(resume_skills)
    job_set = set(job_skills)

    matched = resume_set & job_set
    overlap = len(matched) / len(job_set)

    return min(1.0, overlap)


def find_missing_keywords(
    resume_skills: list[str],
    job_skills: list[str],
) -> list[str]:
    """Find skills required by the job but missing from the resume.

    Args:
        resume_skills: Skills extracted from the resume.
        job_skills: Skills extracted from the job description.

    Returns:
        Sorted list of missing skills.
    """
    resume_set = set(resume_skills)
    job_set = set(job_skills)

    missing = job_set - resume_set
    return sorted(missing)


def compute_section_scores(
    resume_skills: list[str],
    job_skills: list[str],
    resume_text: str,
    job_text: str,
) -> dict:
    """Compute section-level breakdown scores.

    Provides a more detailed view than a single blended number:
    - skills_match: % of job skills found in resume
    - experience_relevance: how well experience section keywords align
    - keyword_density: ratio of skill mentions in resume vs job

    Args:
        resume_skills: Skills extracted from the resume.
        job_skills: Skills extracted from the job description.
        resume_text: Full resume text.
        job_text: Full job description text.

    Returns:
        Dict with section-level scores (0-100 scale).
    """
    # 1. Skills Match — what % of job skills does the resume have?
    skills_match = compute_keyword_overlap(resume_skills, job_skills) * 100

    # 2. Experience Relevance — categorized skill matching
    experience_relevance = _compute_experience_relevance(resume_skills, job_skills)

    # 3. Keyword Density — how many total skill mentions are in the resume
    #    compared to the job (normalized)
    keyword_density = _compute_keyword_density(resume_text, job_text, job_skills)

    return {
        "skills_match": round(skills_match, 2),
        "experience_relevance": round(experience_relevance, 2),
        "keyword_density": round(keyword_density, 2),
    }


def _compute_experience_relevance(
    resume_skills: list[str],
    job_skills: list[str],
) -> float:
    """Score experience relevance by weighting technical skills higher.

    Technical skills (languages, frameworks, databases) are weighted 2x
    compared to soft skills and tools.

    Returns:
        Score from 0 to 100.
    """
    if not job_skills:
        return 100.0

    resume_set = set(resume_skills)
    job_set = set(job_skills)

    # Categorize job skills by importance
    high_value = PROGRAMMING_LANGUAGES | FRAMEWORKS | DATABASES | DATA_ML
    medium_value = CLOUD_DEVOPS | TOOLS_PRACTICES
    low_value = SOFT_SKILLS

    total_weight = 0.0
    matched_weight = 0.0

    for skill in job_set:
        if skill in high_value:
            weight = 3.0
        elif skill in medium_value:
            weight = 2.0
        elif skill in low_value:
            weight = 1.0
        else:
            weight = 1.5

        total_weight += weight
        if skill in resume_set:
            matched_weight += weight

    if total_weight == 0:
        return 100.0

    return (matched_weight / total_weight) * 100


def _compute_keyword_density(
    resume_text: str,
    job_text: str,
    job_skills: list[str],
) -> float:
    """Score keyword density — how frequently job skills appear in the resume.

    Counts occurrences of each job skill in the resume text and compares
    to the job text. Higher density = better tailoring.

    Returns:
        Score from 0 to 100.
    """
    if not job_skills:
        return 100.0

    resume_lower = resume_text.lower()
    job_lower = job_text.lower()

    resume_mentions = 0
    job_mentions = 0

    for skill in job_skills:
        pattern = r"\b" + re.escape(skill) + r"\b"
        try:
            resume_mentions += len(re.findall(pattern, resume_lower))
            job_mentions += len(re.findall(pattern, job_lower))
        except re.error:
            resume_mentions += resume_lower.count(skill)
            job_mentions += job_lower.count(skill)

    if job_mentions == 0:
        return 100.0

    # Ratio of resume mentions to job mentions, capped at 100
    ratio = resume_mentions / job_mentions
    return min(100.0, ratio * 100)
