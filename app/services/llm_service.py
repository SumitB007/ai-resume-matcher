"""LLM Service — OpenRouter API integration for AI feedback, bullet rewrites, and skill extraction.

Supports model switching across OpenRouter providers (Mistral, Llama, GPT, Claude, etc.),
streaming completions via Server-Sent Events (SSE), and intelligent fallbacks.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_MATCH_FEEDBACK = (
    "You are an elite ATS (Applicant Tracking System) optimization specialist and technical resume coach. "
    "Your objective is to provide concrete, highly actionable, and tailored recommendations "
    "to help a candidate bridge skill and experience gaps for a specific job target. "
    "Avoid generic advice. Focus on quantifiable achievements using the Google X-Y-Z formula "
    "('Accomplished [X] as measured by [Y] by doing [Z]') and natural skill integration."
)

SYSTEM_PROMPT_REWRITE_BULLET = (
    "You are an expert resume writer. Given a resume bullet point, optional job context, "
    "and missing skills, rewrite the bullet into a powerful, metrics-driven, action-oriented statement. "
    "Use strong action verbs, quantify impact where possible, and seamlessly integrate target skills."
)


def _get_api_key(override_key: str | None = None) -> str:
    """Resolve OpenRouter API key from parameter or application settings."""
    return override_key or settings.openrouter_api_key or ""


def _get_model(override_model: str | None = None) -> str:
    """Resolve target LLM model name."""
    return override_model or settings.openrouter_default_model or "mistralai/mistral-7b-instruct:free"


async def call_openrouter(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1500,
    api_key: str | None = None,
) -> dict:
    """Send a chat completion request to OpenRouter.

    Args:
        prompt: User prompt content.
        system_prompt: Optional system instruction prompt.
        model: Model identifier (e.g. 'mistralai/mistral-7b-instruct:free', 'openai/gpt-4o-mini').
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in completion.
        api_key: Optional API key override.

    Returns:
        dict: {
            "content": str,
            "model_used": str,
            "usage": dict,
            "fallback_used": bool,
        }
    """
    resolved_key = _get_api_key(api_key)
    target_model = _get_model(model)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    if resolved_key:
        headers = {
            "Authorization": f"Bearer {resolved_key}",
            "HTTP-Referer": "https://github.com/ats-matcher",
            "X-Title": settings.app_name,
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        usage = data.get("usage", {})
                        model_used = data.get("model", target_model)
                        return {
                            "content": content,
                            "model_used": model_used,
                            "usage": usage,
                            "fallback_used": False,
                        }
                else:
                    logger.warning(
                        f"OpenRouter API returned HTTP {response.status_code}: {response.text[:200]}. "
                        "Using intelligent local fallback generator."
                    )
        except Exception as e:
            logger.warning(f"OpenRouter request error: {e}. Using intelligent local fallback generator.")
    else:
        logger.info("No OpenRouter API key configured. Using intelligent local fallback generator.")

    # Intelligent fallback when API key is missing or call fails
    fallback_content = _generate_local_fallback(prompt)
    return {
        "content": fallback_content,
        "model_used": f"{target_model} (offline fallback)",
        "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": len(fallback_content.split()), "total_tokens": len(prompt.split()) + len(fallback_content.split())},
        "fallback_used": True,
    }


async def stream_openrouter(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1500,
    api_key: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream response tokens from OpenRouter using Server-Sent Events.

    Yields text tokens as they arrive. If the API is unreachable, falls back
    to simulated token streaming from the fallback generator.
    """
    resolved_key = _get_api_key(api_key)
    target_model = _get_model(model)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    stream_success = False

    if resolved_key:
        headers = {
            "Authorization": f"Bearer {resolved_key}",
            "HTTP-Referer": "https://github.com/ats-matcher",
            "X-Title": settings.app_name,
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code == 200:
                        stream_success = True
                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content_piece = delta.get("content", "")
                                    if content_piece:
                                        yield content_piece
                            except json.JSONDecodeError:
                                continue
                    else:
                        logger.warning(f"OpenRouter stream returned HTTP {response.status_code}")
        except Exception as e:
            logger.warning(f"OpenRouter stream failed: {e}")

    # Fallback simulation if real streaming was not possible
    if not stream_success:
        fallback_text = _generate_local_fallback(prompt)
        words = fallback_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.02)


async def generate_match_feedback(
    resume_text: str,
    job_text: str,
    missing_keywords: list[str] | None = None,
    section_scores: dict | None = None,
    overall_score: float | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Generate structured AI feedback and recommendations for a resume-job match.

    Args:
        resume_text: Candidate resume content.
        job_text: Target job description.
        missing_keywords: List of detected skill gaps.
        section_scores: Section-level scoring breakdown.
        overall_score: Combined match percentage.
        model: OpenRouter model to use.
        api_key: OpenRouter API key.

    Returns:
        dict: Structured feedback with bullet rewrites and strengths.
    """
    gaps_str = ", ".join(missing_keywords) if missing_keywords else "None detected"
    scores_str = json.dumps(section_scores or {}, indent=2)

    prompt = (
        f"RESUME SNIPPET:\n{resume_text[:2000]}\n\n"
        f"JOB DESCRIPTION:\n{job_text[:2000]}\n\n"
        f"OVERALL MATCH SCORE: {overall_score or 0.0}%\n"
        f"SECTION SCORES:\n{scores_str}\n"
        f"MISSING SKILLS / KEYWORD GAPS: {gaps_str}\n\n"
        "Please provide detailed feedback in the following format:\n"
        "### 1. Strengths & Alignments\n"
        "(Highlight 2-3 specific areas where the candidate strongly matches the job)\n\n"
        "### 2. Critical Skill Gaps & How to Address Them\n"
        "(Identify the top missing skills and where to integrate them naturally)\n\n"
        "### 3. Actionable Bullet-Point Rewrites\n"
        "(Provide 3-4 concrete before-and-after bullet point rewrites using the Google X-Y-Z formula to incorporate missing keywords and metrics)\n\n"
        "### 4. Summary & ATS Strategy\n"
        "(Brief advice on layout, keyword placement, and high-impact changes)"
    )

    result = await call_openrouter(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_MATCH_FEEDBACK,
        model=model,
        temperature=0.7,
        max_tokens=1500,
        api_key=api_key,
    )

    return {
        "feedback_text": result["content"],
        "model_used": result["model_used"],
        "fallback_used": result["fallback_used"],
    }


async def rewrite_bullet_point(
    bullet_point: str,
    job_context: str | None = None,
    missing_skills: list[str] | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Rewrite a single resume bullet point into a quantified, high-impact version.

    Args:
        bullet_point: The original bullet point to improve.
        job_context: Optional description of the target job.
        missing_skills: Skills to prioritize incorporating.
        model: OpenRouter model.
        api_key: API key.

    Returns:
        dict with original, rewritten, explanation, and model_used.
    """
    target_skills_str = ", ".join(missing_skills) if missing_skills else "General backend excellence"
    job_snippet = job_context[:1000] if job_context else "Not specified"

    prompt = (
        f"ORIGINAL BULLET POINT:\n\"{bullet_point}\"\n\n"
        f"TARGET SKILLS TO INTEGRATE IF POSSIBLE: {target_skills_str}\n"
        f"TARGET JOB CONTEXT:\n{job_snippet}\n\n"
        "Rewrite this bullet point into 2 variations:\n"
        "1. Strong & Quantified (X-Y-Z formula: Accomplished [X] as measured by [Y] by doing [Z])\n"
        "2. Keyword-Optimized (seamlessly embeds target technologies)\n\n"
        "Also provide a 1-sentence explanation of why the rewrite is stronger."
    )

    result = await call_openrouter(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_REWRITE_BULLET,
        model=model,
        temperature=0.7,
        max_tokens=800,
        api_key=api_key,
    )

    content = result["content"]

    return {
        "original_bullet": bullet_point,
        "rewrite_content": content,
        "model_used": result["model_used"],
        "fallback_used": result["fallback_used"],
    }


async def extract_skills_llm(
    text: str,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Extract technical skills and domain tools from text using an LLM.

    Args:
        text: Resume or job text.
        model: OpenRouter model.
        api_key: API key.

    Returns:
        dict: {"skills": list[str], "count": int, "model_used": str, "fallback_used": bool}
    """
    system_prompt = (
        "You are an expert NLP technical skill extractor. "
        "Extract all programming languages, frameworks, cloud technologies, databases, DevOps tools, "
        "and architectural patterns mentioned in the text. "
        "Return ONLY a valid JSON array of lowercase strings, for example: [\"python\", \"fastapi\", \"postgresql\"]. "
        "Do not include any commentary, markdown tags, or extra text."
    )
    prompt = f"TEXT TO ANALYZE:\n{text[:3000]}"

    result = await call_openrouter(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=0.1,
        max_tokens=600,
        api_key=api_key,
    )

    raw_content = result["content"].strip()
    # Strip markdown block if model output ```json ... ```
    if raw_content.startswith("```"):
        raw_content = raw_content.split("```")[1]
        if raw_content.startswith("json"):
            raw_content = raw_content[4:]
        raw_content = raw_content.strip()

    skills = []
    try:
        parsed = json.loads(raw_content)
        if isinstance(parsed, list):
            skills = sorted(list(set(str(s).strip().lower() for s in parsed if str(s).strip())))
    except Exception:
        # Fall back to regex extractor
        from app.services.keyword_service import extract_skills
        skills = extract_skills(text)

    return {
        "skills": skills,
        "count": len(skills),
        "model_used": result["model_used"],
        "fallback_used": result["fallback_used"],
    }


def _generate_local_fallback(prompt: str) -> str:
    """Generate high-quality, domain-specific fallback feedback when OpenRouter API is unavailable."""
    prompt_lower = prompt.lower()

    if "rewrite this bullet point" in prompt_lower or "original bullet point" in prompt_lower:
        return (
            "### Recommended Rewrites\n\n"
            "**Variation 1 — Strong & Quantified (Google X-Y-Z Formula):**\n"
            "• Spearheaded the re-architecture of core backend microservices utilizing FastAPI and PostgreSQL, "
            "reducing API latency by 42% and scaling request throughput to 15,000 requests/minute.\n\n"
            "**Variation 2 — Keyword & Performance Optimized:**\n"
            "• Designed and implemented distributed caching and background job pipelines with Redis and Celery, "
            "improving data synchronization speeds by 65% and achieving 99.98% service uptime.\n\n"
            "**Why this is stronger:** The rewrites transform a passive task description into an active achievement "
            "with tangible business impact and clear metrics."
        )

    # General Match Feedback fallback
    return (
        "### 1. Strengths & Alignments\n"
        "• **Core Technical Synergy**: The candidate exhibits strong alignment in core backend fundamentals, "
        "including Python, RESTful API architecture, and relational database management.\n"
        "• **Production Experience**: Demonstrated track record designing scalable microservices and implementing "
        "automated test pipelines with pytest.\n\n"
        "### 2. Critical Skill Gaps & How to Address Them\n"
        "• **Distributed Systems & Caching**: The job description emphasizes Redis caching, asynchronous processing, and message queues. "
        "Ensure these competencies are explicitly stated in your skills section and illustrated in project bullet points.\n"
        "• **Cloud & Container Orchestration**: Highlight practical experience with Docker, Kubernetes, and CI/CD deployment pipelines.\n\n"
        "### 3. Actionable Bullet-Point Rewrites (Google X-Y-Z Formula)\n"
        "• **Before:** \"Managed database and wrote APIs for web application.\"\n"
        "  **After:** \"Architected high-throughput RESTful APIs with FastAPI and PostgreSQL, optimizing database queries to reduce p99 response times from 350ms to 45ms.\"\n"
        "• **Before:** \"Used Redis for caching and background tasks.\"\n"
        "  **After:** \"Implemented Redis-based caching and Celery task queues, eliminating duplicate database computations and increasing concurrent user capacity by 3x.\"\n"
        "• **Before:** \"Deployed applications using Docker.\"\n"
        "  **After:** \"Containerized 5+ microservices with Docker and orchestrated deployments using Kubernetes, cutting deployment rollback times by 80%.\"\n\n"
        "### 4. Summary & ATS Strategy\n"
        "• Add a dedicated **'Core Technical Competencies'** section near the top of the resume featuring all target keywords.\n"
        "• Integrate missing keywords directly inside job achievement statements rather than listing them in isolation to maximize ATS contextual relevance."
    )


SYSTEM_PROMPT_COVER_LETTER = (
    "You are an expert cover-letter writer. You write specific, credible letters "
    "grounded only in facts from the candidate's resume — never invent employers, "
    "metrics, or experience the resume does not state. Output ONLY the letter's "
    "body paragraphs, separated by blank lines: no greeting line, no sign-off, "
    "no placeholders like [Your Name], no markdown."
)

_TONE_GUIDANCE = {
    "professional": "measured and confident; standard business register",
    "enthusiastic": "warm and energetic; clear genuine enthusiasm for this company and role, without hype",
    "concise": "tight and direct; shorter paragraphs, every sentence earning its place",
}


def _structured_fallback_letter(
    *,
    candidate_name: str,
    candidate_title: str,
    years: str,
    matched_skills: list[str],
    missing_skills: list[str],
    job_title: str,
    company: str,
    tone: str,
) -> list[str]:
    """Deterministic cover letter used when no LLM is available (Phase 14).

    Same contract as the rest of the product's fallbacks: degraded but fully
    functional, built only from facts extracted from the resume and JD —
    matched skills are real (dictionary intersection), missing skills are
    framed as learning goals, never as experience.
    """
    role = job_title or "the advertised role"
    org = company or "your company"
    title_bit = candidate_title or "developer"
    years_bit = f" with {years} of experience" if years else ""
    top = matched_skills[:5]
    skills_sentence = (
        f"My background covers {', '.join(top[:-1])} and {top[-1]}"
        if len(top) > 1
        else (f"My background covers {top[0]}" if top else "My background is in software development")
    )

    if tone == "enthusiastic":
        p1 = (
            f"I was excited to see the {role} opening at {org} — it lines up closely with the work I most enjoy. "
            f"I am a {title_bit}{years_bit}, and I am applying because the role reads like a description of my current day-to-day work and where I want to take it next."
        )
    elif tone == "concise":
        p1 = (
            f"I am applying for the {role} position at {org}. "
            f"I am a {title_bit}{years_bit}, and my experience matches the core requirements of the role."
        )
    else:
        p1 = (
            f"I am writing to apply for the {role} position at {org}. "
            f"As a {title_bit}{years_bit}, I have focused on exactly the kind of work this role describes, and I would welcome the opportunity to bring that experience to your team."
        )

    p2 = (
        f"{skills_sentence} — the technologies at the centre of this role. "
        "In my recent work I have shipped production systems with these tools, owned features end to end, "
        "and measured my work by its reliability and impact rather than by output alone. "
        "The details are in my resume; the short version is that the strongest requirements in your description are the parts of my background I use every day."
    )
    if tone == "concise":
        p2 = (
            f"{skills_sentence} — the core stack for this role. "
            "I have shipped production systems with these tools and owned features end to end; my resume has the specifics."
        )

    if missing_skills:
        bridge = ", ".join(missing_skills[:2])
        p3 = (
            f"To be straightforward about fit: {bridge} is an area I am actively building depth in, and I am honest about that rather than overselling it. "
            f"What I offer {org} today is strength in the core of the role, plus a track record of picking up adjacent technology quickly when a project demands it."
        )
    elif tone == "enthusiastic":
        p3 = (
            f"Beyond the technical match, {org} is the kind of team I want to build with — the role's scope, from ownership to impact, is exactly the direction I am growing in. "
            "I would love the chance to talk through how my recent projects map onto what you are hiring for."
        )
    else:
        p3 = (
            f"What I would bring to {org} beyond the technical match is ownership: I am used to being accountable for outcomes — for systems staying up, deadlines being met honestly, and teammates being able to build on my work. "
            "That is the standard I would expect to be held to in this role as well."
        )

    p4 = (
        "Thank you for considering my application. I would appreciate the opportunity to discuss how my experience fits what you are building, and I am available for a conversation at your convenience."
        if tone != "concise"
        else "Thank you for your consideration — I would welcome a conversation about the role."
    )
    return [p1, p2, p3, p4]


async def generate_cover_letter(
    resume_text: str,
    job_text: str,
    job_title: str = "",
    company: str = "",
    tone: str = "professional",
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Generate cover-letter body paragraphs for a resume + job pair (Phase 14).

    Returns {"paragraphs": list[str], "model_used": str, "fallback_used": bool}.
    Uses the LLM when available; otherwise (or when the LLM output is
    unusable) a structured deterministic letter built from extracted facts.
    Greeting and sign-off are structural fields owned by the letter document,
    not generated here.
    """
    import re as _re

    from app.services.keyword_service import extract_skills

    tone = tone if tone in _TONE_GUIDANCE else "professional"
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_text)
    matched = [s for s in job_skills if s in resume_skills]
    missing = [s for s in job_skills if s not in resume_skills]

    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    candidate_name = lines[0] if lines else ""
    candidate_title = lines[1] if len(lines) > 1 and "@" not in lines[1] else ""
    years_match = _re.search(r"(\d+)\+?\s*years?", resume_text, _re.I)
    years = f"{years_match.group(1)} years" if years_match else ""

    def fallback(reason_model: str) -> dict:
        return {
            "paragraphs": _structured_fallback_letter(
                candidate_name=candidate_name,
                candidate_title=candidate_title,
                years=years,
                matched_skills=matched,
                missing_skills=missing,
                job_title=job_title,
                company=company,
                tone=tone,
            ),
            "model_used": reason_model,
            "fallback_used": True,
        }

    if not _get_api_key(api_key):
        return fallback("structured template (no LLM key)")

    prompt = (
        f"Write a cover letter body for this application.\n"
        f"ROLE: {job_title or 'the role'} at {company or 'the company'}\n"
        f"TONE: {_TONE_GUIDANCE[tone]}\n"
        f"Write 4 paragraphs: (1) why this role and background fit, (2) evidence from the resume "
        f"for the role's core requirements ({', '.join(matched[:6]) or 'the resume skills'}), "
        f"(3) an honest, brief bridge for gaps ({', '.join(missing[:3]) or 'none'}) framed as growth, never as experience, "
        f"(4) a closing with a call to conversation.\n\n"
        f"RESUME:\n{resume_text[:2500]}\n\nJOB DESCRIPTION:\n{job_text[:2000]}"
    )
    result = await call_openrouter(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT_COVER_LETTER,
        model=model,
        temperature=0.7,
        max_tokens=900,
        api_key=api_key,
    )
    if result["fallback_used"]:
        return fallback(result["model_used"])

    raw = result["content"].strip()
    paragraphs = [
        p.strip().strip("#").strip()
        for p in raw.split("\n\n")
        if len(p.strip()) > 40 and not p.strip().lower().startswith(("dear ", "sincerely", "best regards", "warm regards"))
    ]
    if len(paragraphs) < 3 or sum(len(p) for p in paragraphs) < 300:
        return fallback(result["model_used"])

    return {
        "paragraphs": paragraphs[:5],
        "model_used": result["model_used"],
        "fallback_used": False,
    }
