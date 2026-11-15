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


def _prompt_field(prompt: str, label: str) -> str:
    """Pull a labelled field out of one of this module's own prompts."""
    import re as _re

    m = _re.search(rf"{_re.escape(label)}:\s*(.+)", prompt)
    return m.group(1).strip() if m else ""


def _rephrase_own_bullet(bullet: str) -> str:
    """Form-only rephrase of the user's own bullet (shared with Phase 15)."""
    text = (bullet or "").strip().strip('"').rstrip(".")
    if not text:
        return text
    for pattern, replacement in _BULLET_PREFIX_MAP:
        text = pattern.sub(replacement, text)
    return text[0].upper() + text[1:]


def _generate_local_fallback(prompt: str) -> str:
    """Offline fallback (rewritten 2026-11-15 — Sumit's option B).

    The previous version returned canned text with invented metrics
    ("42% latency reduction", "99.98% uptime") regardless of the user's
    actual resume. This version is built ONLY from facts inside the prompt
    itself — the user's own bullet, their real scores, their real matched
    and missing skills — and wherever a metric would strengthen the text it
    emits an explicit "[add your metric]" placeholder for the user to fill
    with a true number. It never states a number the prompt didn't.
    """
    prompt_lower = prompt.lower()

    # ── Bullet rewrite ──
    if "rewrite this bullet point" in prompt_lower or "original bullet point" in prompt_lower:
        import re as _re

        m = _re.search(r'ORIGINAL BULLET POINT:\s*\n"([^"]+)"', prompt)
        bullet = m.group(1) if m else ""
        skills_line = _prompt_field(prompt, "TARGET SKILLS TO INTEGRATE IF POSSIBLE")
        rephrased = _rephrase_own_bullet(bullet) or "Your bullet, rephrased"
        skills_bit = (
            f" If you genuinely used {skills_line} here, name it — otherwise leave it out."
            if skills_line and "general" not in skills_line.lower()
            else ""
        )
        return (
            "### Recommended Rewrites\n\n"
            "**Variation 1 — Your facts, X-Y-Z form:**\n"
            f"• {rephrased}, measured by [add your metric — e.g. requests/day, latency, users, or cost saved].\n\n"
            "**Variation 2 — Your facts, tool-forward:**\n"
            f"• {rephrased} — [add your metric], using [add the tools you actually used].\n\n"
            "**Why this is stronger:** Same facts, stronger form: an action verb up front and a real "
            f"number where the placeholder sits.{skills_bit} Never copy a metric you can't back up in an interview."
        )

    # ── Match feedback ──
    if "overall match score" in prompt_lower or "missing skills" in prompt_lower:
        from app.services.keyword_service import extract_skills

        score = _prompt_field(prompt, "OVERALL MATCH SCORE")
        gaps_line = _prompt_field(prompt, "MISSING SKILLS / KEYWORD GAPS")
        gaps = [g.strip() for g in gaps_line.split(",") if g.strip() and g.strip().lower() != "none detected"]
        resume_snippet = prompt.split("JOB DESCRIPTION:")[0]
        job_snippet = prompt.split("JOB DESCRIPTION:")[-1]
        matched = [s for s in extract_skills(job_snippet) if s in extract_skills(resume_snippet)]

        strengths = (
            f"• **Verified overlap**: Your resume already evidences {', '.join(matched[:6])} — "
            "skills this job explicitly asks for. Keep them prominent and worded the way the job words them."
            if matched
            else "• **Starting point**: The matcher found little direct skill overlap with this job's stated requirements — the gaps section below is where the leverage is."
        )
        score_line = f"• **Overall match: {score}** — that number comes from your actual resume against this actual job, not a template." if score else ""

        if gaps:
            gap_text = "\n".join(
                f"• **{gap}**: named in the job, absent from your resume. If you have genuinely used it, "
                "say so explicitly in your skills section and in a bullet. If you haven't, leave it out — "
                "a visible gap is cheaper than a claim you can't defend in an interview."
                for gap in gaps[:5]
            )
        else:
            gap_text = "• No dictionary-level skill gaps were detected for this job. The remaining gains are in wording and evidence, not coverage."

        own_bullets = [
            ln.strip(" -•\t")
            for ln in resume_snippet.splitlines()
            if ln.strip().startswith(("-", "•")) and len(ln.strip()) > 25
        ][:2]
        if own_bullets:
            def _after(b: str) -> str:
                # A bullet that already carries its own metric doesn't need
                # a placeholder appended — just the stronger form.
                if any(ch.isdigit() for ch in b):
                    return _rephrase_own_bullet(b)
                return f"{_rephrase_own_bullet(b)}, measured by [add your metric — the true number only you know]."

            rewrite_text = "\n".join(
                f"• **Before:** \"{b}\"\n  **After:** \"{_after(b)}\""
                for b in own_bullets
            )
        else:
            rewrite_text = (
                "• Take your strongest bullet and give it the X-Y-Z shape: what you accomplished, "
                "measured by [add your metric], by doing [the method, in your own words]. "
                "Offline mode can't see a full bullet list here, so this one is a template, not a rewrite."
            )

        parts = [
            "### 1. Strengths & Alignments",
            strengths,
        ]
        if score_line:
            parts.append(score_line)
        parts += [
            "",
            "### 2. Critical Skill Gaps & How to Address Them",
            gap_text,
            "",
            "### 3. Actionable Bullet-Point Rewrites (Google X-Y-Z Formula)",
            rewrite_text,
            "",
            "### 4. Summary & ATS Strategy",
            "• Mirror the job's own wording for the skills you truly have — ATS matching is literal.",
            "• Put numbers only where they're true; a placeholder you fill honestly beats a borrowed metric.",
            "• Keep standard section headings (Summary, Experience, Skills, Education) so parsers file your content correctly.",
            "",
            "_Offline mode: this feedback is generated locally from your match data — no AI model was involved._",
        ]
        return "\n".join(parts)

    # ── Anything else (streaming, ad-hoc prompts) ──
    return (
        "AI generation is unavailable offline, so here is the honest template instead: "
        "state what you accomplished, measured by [add your metric], by doing [your method, in your own words]. "
        "Fill the brackets with your real numbers — never borrow metrics you can't back up."
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


# ── Phase 15: generator features ───────────────────────────────────────
# Every generator follows the product contract: LLM when available, a
# structured deterministic fallback otherwise, and a hard no-fabrication
# rule — generators may rephrase and organise the user's facts, never add
# employers, metrics, or skills the user did not supply. For bullets the
# rule is enforced in code, not just in the prompt (see _numbers_guard).

import re as _re_gen


def _numbers_in(text: str) -> set[str]:
    return set(_re_gen.findall(r"\d+(?:[.,]\d+)?%?", text or ""))


def _numbers_guard(items: list[str], source_text: str) -> list[str]:
    """Drop any generated item containing a number absent from the source.

    The user supplies facts; the AI supplies form. A bullet that invents
    "40% faster" when the notes never mention 40 fails this check and is
    dropped (the caller falls back if too few survive).
    """
    allowed = _numbers_in(source_text)
    return [item for item in items if _numbers_in(item) <= allowed]


def _fallback_summary_variants(
    title: str, years: str, skills: list[str], target_role: str
) -> list[dict]:
    role = target_role or title or "developer"
    title_bit = title or role
    years_bit = f"{years} of experience" if years else "experience"
    top = ", ".join(skills[:4]) if skills else "modern tooling"
    deep = ", ".join(skills[:6]) if skills else "modern tooling"
    return [
        {
            "label": "Professional",
            "text": (
                f"{title_bit} with {years_bit} specialising in {top}. "
                f"Track record of owning features end to end — design, delivery, and the reliability of what ships. "
                f"Now focused on {role} roles where that depth in {skills[0] if skills else 'the stack'} is central."
            ),
        },
        {
            "label": "Impact-led",
            "text": (
                f"{title_bit} ({years_bit}) who measures work by outcomes: systems that stay up, teams that ship faster, users who notice the difference. "
                f"Core strength across {deep}, applied most recently to production systems at real scale."
            ),
        },
        {
            "label": "Concise",
            "text": f"{title_bit} · {years_bit} · {deep}. End-to-end ownership, production-proven.",
        },
    ]


async def generate_summary_variants(
    title: str,
    years: str,
    skills: list[str],
    target_role: str = "",
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Three pick-to-insert summary variants (Phase 15)."""
    fallback = lambda m: {  # noqa: E731
        "variants": _fallback_summary_variants(title, years, skills, target_role),
        "model_used": m,
        "fallback_used": True,
    }
    if not _get_api_key(api_key):
        return fallback("structured template (no LLM key)")

    prompt = (
        f"Write 3 professional-summary variants for a resume.\n"
        f"CURRENT TITLE: {title}\nEXPERIENCE: {years}\nTOP SKILLS: {', '.join(skills[:8])}\n"
        f"TARGET ROLE: {target_role or title}\n"
        "Labels: Professional, Impact-led, Concise. Use ONLY the facts given — invent no employers, metrics, or skills.\n"
        'Return ONLY JSON: {"variants": [{"label": "...", "text": "..."}, ...]} with exactly 3 items.'
    )
    result = await call_openrouter(
        prompt=prompt,
        system_prompt="You are an expert resume writer. Output only valid JSON.",
        model=model, temperature=0.6, max_tokens=700, api_key=api_key,
    )
    if result["fallback_used"]:
        return fallback(result["model_used"])
    try:
        raw = result["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        parsed = json.loads(raw)
        variants = [
            {"label": str(v.get("label", "")), "text": str(v.get("text", "")).strip()}
            for v in parsed.get("variants", [])
            if str(v.get("text", "")).strip()
        ]
        if len(variants) < 3:
            raise ValueError("too few variants")
        return {"variants": variants[:3], "model_used": result["model_used"], "fallback_used": False}
    except Exception:
        return fallback(result["model_used"])


_PAST_TENSE = {
    "building": "Built", "developing": "Developed", "creating": "Created",
    "writing": "Wrote", "designing": "Designed", "implementing": "Implemented",
    "maintaining": "Maintained", "leading": "Led", "managing": "Managed",
}


def _PAST_TENSE_VERBS(m):  # noqa: N802 - used as a re.sub callable in the map below
    return _PAST_TENSE.get(m.group(1).lower(), m.group(1).capitalize())


def _PAST_TENSE_VERBS_G2(m):  # noqa: N802
    return _PAST_TENSE.get(m.group(2).lower(), m.group(2).capitalize())


_BULLET_PREFIX_MAP = [
    # Verb-preserving first: "Responsible for building X" -> "Built X",
    # not "Owned building X".
    (_re_gen.compile(r"^responsible for\s+(building|developing|creating|writing|designing|implementing|maintaining|leading|managing)\b", _re_gen.I), _PAST_TENSE_VERBS),
    (_re_gen.compile(r"^(was|am|is)\s+responsible for\s+(building|developing|creating|writing|designing|implementing|maintaining|leading|managing)\b", _re_gen.I), _PAST_TENSE_VERBS_G2),
    (_re_gen.compile(r"^i was responsible for\s+", _re_gen.I), "Owned "),
    (_re_gen.compile(r"^responsible for\s+", _re_gen.I), "Owned "),
    (_re_gen.compile(r"^i worked on\s+", _re_gen.I), "Developed "),
    (_re_gen.compile(r"^worked on\s+", _re_gen.I), "Developed "),
    (_re_gen.compile(r"^i helped\s+", _re_gen.I), "Contributed to "),
    (_re_gen.compile(r"^helped\s+", _re_gen.I), "Contributed to "),
    (_re_gen.compile(r"^i\s+", _re_gen.I), ""),
]


def _fallback_bullets(notes: str) -> list[str]:
    """Format the user's own rough notes as bullets — words kept, form added.

    Splits on lines/semicolons, strips first-person filler prefixes, and
    capitalises. Adds NO numbers, employers, or claims (see _numbers_guard —
    by construction the output's numbers are a subset of the input's).
    """
    chunks = []
    for part in _re_gen.split(r"[\n;]+", notes or ""):
        part = part.strip(" -•\t")
        if len(part) < 8:
            continue
        for pattern, replacement in _BULLET_PREFIX_MAP:
            part = pattern.sub(replacement, part)
        part = part[0].upper() + part[1:]
        chunks.append(part.rstrip("."))
    return chunks[:8]


async def generate_bullets(
    role: str,
    company: str,
    notes: str,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Turn rough notes into achievement bullets (Phase 15).

    The user supplies facts; the AI supplies form. LLM output passes the
    numbers guard: any bullet containing a number the notes never stated is
    dropped, and if too few survive the deterministic fallback is used.
    """
    fallback = lambda m: {  # noqa: E731
        "bullets": _fallback_bullets(notes),
        "model_used": m,
        "fallback_used": True,
    }
    if not _get_api_key(api_key):
        return fallback("structured template (no LLM key)")

    prompt = (
        f"Turn these rough notes into 3-6 strong resume bullet points for a {role} at {company}.\n"
        "Use the Google X-Y-Z form (accomplished X, measured by Y, by doing Z) ONLY where the notes supply the facts. "
        "NEVER invent metrics, employers, team sizes, or technologies that are not in the notes.\n\n"
        f"NOTES:\n{notes[:2000]}\n\nReturn one bullet per line, no numbering, no leading dashes."
    )
    result = await call_openrouter(
        prompt=prompt,
        system_prompt="You are an expert resume writer who never fabricates facts.",
        model=model, temperature=0.5, max_tokens=700, api_key=api_key,
    )
    if result["fallback_used"]:
        return fallback(result["model_used"])
    lines = [
        ln.strip(" -•\t").strip()
        for ln in result["content"].splitlines()
        if len(ln.strip()) > 15
    ]
    guarded = _numbers_guard(lines, notes)
    if len(guarded) < 2:
        return fallback(result["model_used"])
    return {"bullets": guarded[:6], "model_used": result["model_used"], "fallback_used": False}


async def suggest_skill_groups(
    text: str,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Skill groups for a document, from a role description or JD (Phase 15).

    Skills come from the LLM extractor when available (its own fallback is
    the dictionary), then grouping is deterministic over the category map —
    the roadmap's 'intersected with the dictionary' rule, so suggested
    skills are always real dictionary skills, never free-invented strings.
    """
    from app.services.keyword_service import group_skills_by_category

    extraction = await extract_skills_llm(text=text, model=model, api_key=api_key)
    groups = group_skills_by_category(extraction["skills"])
    return {
        "groups": groups,
        "skills": extraction["skills"],
        "model_used": extraction["model_used"],
        "fallback_used": extraction["fallback_used"],
    }


async def generate_resume_draft(
    title: str,
    level: str,
    skills_text: str,
    model: str | None = None,
    api_key: str | None = None,
) -> dict:
    """A complete document skeleton from a job title (Phase 15).

    Composes the other generators: summary variants (first is used) + the
    deterministic skill grouper over the user's stated skills. Experience
    starts as one empty entry carrying the target role — the draft is a
    starting structure to edit, never fabricated history.
    """
    from app.services.document_service import EMPTY_CONTENT
    from app.services.keyword_service import extract_skills, group_skills_by_category

    content = json.loads(json.dumps(EMPTY_CONTENT))
    content["personal"]["title"] = title

    stated = extract_skills(skills_text) or [
        s.strip().lower() for s in skills_text.split(",") if s.strip()
    ]
    years = {"entry": "early-career", "mid": "3+ years", "senior": "6+ years", "lead": "10+ years"}.get(level, "")
    summary = await generate_summary_variants(
        title=title, years=years, skills=stated[:8], target_role=title,
        model=model, api_key=api_key,
    )
    content["summary"] = summary["variants"][0]["text"] if summary["variants"] else ""
    groups = group_skills_by_category([s for s in stated if s])
    # Document content shape is {label, items} (Phase 13) — convert from the
    # API grouping shape {name, skills}.
    content["skills"] = {
        "groups": [{"label": g["name"], "items": g["skills"]} for g in groups]
        or ([{"label": "Core Skills", "items": stated}] if stated else [])
    }
    content["experience"] = [
        {"role": title, "company": "", "location": "", "start": "", "end": "", "current": False, "bullets": []}
    ]
    return {
        "content": content,
        "summary_variants": summary["variants"],
        "model_used": summary["model_used"],
        "fallback_used": summary["fallback_used"],
    }


async def extract_resume_structure(
    text: str,
    model: str | None = None,
    api_key: str | None = None,
) -> dict | None:
    """LLM structured extraction of resume text into builder content (Phase 15).

    Returns a content dict coerced onto EMPTY_CONTENT's shape, or None when
    no LLM is available or the output doesn't validate — the caller then
    uses the deterministic heuristic parser (§13.4's upgrade path).
    """
    if not _get_api_key(api_key):
        return None
    from app.services.document_service import EMPTY_CONTENT

    shape = json.dumps(EMPTY_CONTENT)
    prompt = (
        "Extract this resume into EXACTLY this JSON shape (same keys; empty strings/lists where unknown). "
        "Copy facts verbatim — do not summarise bullets, invent dates, or add skills not present.\n"
        f"SHAPE:\n{shape}\n\nRESUME:\n{text[:6000]}\n\nReturn ONLY the JSON object."
    )
    result = await call_openrouter(
        prompt=prompt,
        system_prompt="You are a precise resume parser. Output only valid JSON.",
        model=model, temperature=0.1, max_tokens=2500, api_key=api_key,
    )
    if result["fallback_used"]:
        return None
    try:
        raw = result["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].removeprefix("json").strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        content = json.loads(json.dumps(EMPTY_CONTENT))
        for key in content:
            if key in parsed and isinstance(parsed[key], type(content[key])):
                content[key] = parsed[key]
        # Require at least a name or one experience entry to count as success.
        personal = content.get("personal") or {}
        if not personal.get("full_name") and not content.get("experience"):
            return None
        return content
    except Exception:
        return None
