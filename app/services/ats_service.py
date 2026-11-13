"""Standalone ATS readiness checker (Phase 11 of the product — roadmap Phase 2).

WHY RULE-BASED, NOT AN LLM (decisions.md §12.1):
An ATS check must be deterministic (same resume → same result, every time),
instant, free to run, and explainable line-by-line. Every check here is a
transparent rule over the extracted resume text, identified by a stable id so
results stay comparable across versions of the checker.

This score is an *ATS-readiness* score: how well the resume parses and reads
to an applicant tracking system. It is deliberately NOT a job-match score —
that is matching_service's job and requires a job description.

The service is pure (text in, result dict out, no DB/IO) so it can be unit
tested without infrastructure and reused by both the authenticated endpoint
(persisted) and the anonymous public checker (never persisted).
"""

import re

from app.services.keyword_service import extract_skills

# ── Tunables ────────────────────────────────────────────────────────────────

ACTION_VERBS = {
    "achieved", "automated", "built", "collaborated", "created", "debugged",
    "delivered", "designed", "developed", "drove", "engineered", "enhanced",
    "implemented", "improved", "increased", "integrated", "launched", "led",
    "maintained", "managed", "mentored", "migrated", "optimized", "owned",
    "reduced", "refactored", "resolved", "scaled", "shipped", "simplified",
    "streamlined", "supported", "tested", "trained", "wrote",
}

BULLET_PREFIXES = ("•", "-", "*", "▪", "◦", "·", "–")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
LINK_RE = re.compile(r"(https?://|www\.|linkedin\.com|github\.com)", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
FIRST_PERSON_RE = re.compile(r"\b(I|me|my|mine|we|our|us)\b")

SECTION_PATTERNS = {
    "summary": re.compile(r"\b(summary|professional profile|profile|objective|about me)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|employment history|work history|professional experience)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|academic background|qualifications)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(skills|technical skills|technologies|tech stack|core competencies)\b", re.IGNORECASE),
}

STATUS_VALUE = {"pass": 1.0, "warn": 0.5, "fail": 0.0}


def _check(check_id, group, label, status, detail, weight=1):
    return {
        "id": check_id,
        "group": group,
        "label": label,
        "status": status,
        "detail": detail,
        "weight": weight,
    }


def _band(value, pass_at, warn_at, invert=False):
    """Map a numeric value to pass/warn/fail. invert=True: lower is better."""
    if invert:
        if value <= pass_at:
            return "pass"
        if value <= warn_at:
            return "warn"
        return "fail"
    if value >= pass_at:
        return "pass"
    if value >= warn_at:
        return "warn"
    return "fail"


def run_ats_checks(raw_text: str, parsed_skills: list[str] | None = None) -> dict:
    """Run all ATS readiness checks against extracted resume text.

    Returns {"score": float 0-100, "groups": {group: score}, "checks": [...],
             "word_count": int, "skills_found": [..]}.
    """
    text = raw_text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    words = re.findall(r"[A-Za-z][A-Za-z'+\-#]*", text)
    word_count = len(words)
    lower = text.lower()

    if parsed_skills is None:
        parsed_skills = extract_skills(text)

    bullet_lines = [ln for ln in lines if ln.startswith(BULLET_PREFIXES)]
    # Some parsers strip bullet glyphs; fall back to short achievement lines.
    if len(bullet_lines) < 3:
        bullet_lines = [
            ln for ln in lines
            if 4 <= len(ln.split()) <= 30 and ln[0].isupper()
        ][:40]

    checks: list[dict] = []

    # ── Group: file_parse ───────────────────────────────────────────────────
    char_count = len(text.strip())
    checks.append(_check(
        "text_extractable", "file_parse", "Text extracts cleanly",
        _band(char_count, 800, 200),
        f"{char_count} characters extracted. Image-only/scanned PDFs yield little or no text, and ATS systems cannot read them.",
        weight=2,
    ))

    letter_words = [w for w in words if any(c.isalpha() for c in w)]
    letter_ratio = (len(letter_words) / word_count * 100) if word_count else 0
    checks.append(_check(
        "no_garbled_text", "file_parse", "No garbled / OCR-broken text",
        _band(letter_ratio, 85, 70),
        f"{letter_ratio:.0f}% of tokens look like real words. Low ratios suggest a scanned or corrupted file.",
    ))

    checks.append(_check(
        "has_structure_lines", "file_parse", "Content spans multiple lines",
        _band(len(lines), 15, 6),
        f"{len(lines)} non-empty lines. A resume collapsed into one block usually means a layout the parser mangled.",
    ))

    # ── Group: contact ──────────────────────────────────────────────────────
    checks.append(_check(
        "email_present", "contact", "Email address present",
        "pass" if EMAIL_RE.search(text) else "fail",
        "An email in the resume body is how recruiters reach you; ATS parsers look for it explicitly.",
        weight=2,
    ))

    checks.append(_check(
        "phone_present", "contact", "Phone number present",
        "pass" if PHONE_RE.search(text) else "warn",
        "No phone-like number found. Many ATS application forms require one.",
    ))

    checks.append(_check(
        "links_present", "contact", "LinkedIn / portfolio / GitHub link",
        "pass" if LINK_RE.search(text) else "warn",
        "A LinkedIn, GitHub, or portfolio URL strengthens the application and is parsed as a contact field.",
    ))

    # ── Group: sections ─────────────────────────────────────────────────────
    checks.append(_check(
        "has_summary", "sections", "Summary / profile section",
        "pass" if SECTION_PATTERNS["summary"].search(text) else "warn",
        "A short summary heading helps parsers (and recruiters) place your profile quickly.",
    ))

    checks.append(_check(
        "has_experience", "sections", "Experience section",
        "pass" if SECTION_PATTERNS["experience"].search(text) else "fail",
        "No recognisable experience heading found. Use a standard heading like 'Experience' or 'Work History'.",
        weight=2,
    ))

    checks.append(_check(
        "has_education", "sections", "Education section",
        "pass" if SECTION_PATTERNS["education"].search(text) else "warn",
        "No education heading found. If you have formal education, label the section plainly.",
    ))

    checks.append(_check(
        "has_skills_section", "sections", "Skills section",
        "pass" if SECTION_PATTERNS["skills"].search(text) else "warn",
        "A labelled skills section is the single easiest place for an ATS to harvest keywords.",
    ))

    exp_match = SECTION_PATTERNS["experience"].search(text)
    edu_match = SECTION_PATTERNS["education"].search(text)
    order_ok = bool(exp_match and edu_match and exp_match.start() < edu_match.start())
    checks.append(_check(
        "section_order", "sections", "Experience listed before education",
        "pass" if order_ok else "warn",
        "For experienced candidates, Experience above Education is the conventional, parser-friendly order.",
    ))

    # ── Group: content ──────────────────────────────────────────────────────
    checks.append(_check(
        "bullet_count", "content", "Achievement bullets present",
        _band(len(bullet_lines), 8, 4),
        f"{len(bullet_lines)} bullet lines found. Responsibilities and achievements read best as bullets, not paragraphs.",
    ))

    quantified = [ln for ln in bullet_lines if re.search(r"\d", ln)]
    quantified_pct = (len(quantified) / len(bullet_lines) * 100) if bullet_lines else 0
    checks.append(_check(
        "quantified_bullets", "content", "Bullets include numbers / impact",
        _band(quantified_pct, 30, 15),
        f"{quantified_pct:.0f}% of bullets contain a number. Quantified impact (%, $, counts, time saved) is what separates strong bullets.",
    ))

    verb_led = [
        ln for ln in bullet_lines
        if ln.lstrip("•-*▪◦·– ").split(" ")[0].lower().strip(",") in ACTION_VERBS
    ]
    verb_pct = (len(verb_led) / len(bullet_lines) * 100) if bullet_lines else 0
    checks.append(_check(
        "action_verbs", "content", "Bullets start with action verbs",
        _band(verb_pct, 50, 25),
        f"{verb_pct:.0f}% of bullets start with a strong action verb (built, led, shipped…).",
    ))

    fp_count = len(FIRST_PERSON_RE.findall(text))
    fp_per_100 = (fp_count / word_count * 100) if word_count else 0
    checks.append(_check(
        "first_person", "content", "Minimal first-person pronouns",
        _band(fp_per_100, 1.0, 3.0, invert=True),
        f"{fp_count} first-person pronouns (I / my / we). Resume convention drops them: 'Built…' not 'I built…'.",
    ))

    avg_bullet_words = (
        sum(len(ln.split()) for ln in bullet_lines) / len(bullet_lines)
        if bullet_lines else 0
    )
    if 8 <= avg_bullet_words <= 25:
        bullet_len_status = "pass"
    elif 5 <= avg_bullet_words <= 32:
        bullet_len_status = "warn"
    else:
        bullet_len_status = "fail"
    checks.append(_check(
        "bullet_length", "content", "Bullet length is readable",
        bullet_len_status,
        f"Bullets average {avg_bullet_words:.0f} words. One to two lines each (roughly 8–25 words) is the readable range.",
    ))

    # ── Group: skills ───────────────────────────────────────────────────────
    checks.append(_check(
        "skills_detected", "skills", "Recognisable skills found",
        _band(len(parsed_skills), 10, 5),
        f"{len(parsed_skills)} skills recognised from the tech dictionary. ATS keyword filters can only match skills that appear verbatim.",
        weight=2,
    ))

    bullet_text = "\n".join(bullet_lines).lower()
    skills_in_bullets = [s for s in parsed_skills if s.lower() in bullet_text]
    in_bullets_pct = (
        len(skills_in_bullets) / len(parsed_skills) * 100 if parsed_skills else 0
    )
    checks.append(_check(
        "skills_in_context", "skills", "Skills shown in bullets, not just listed",
        _band(in_bullets_pct, 40, 20),
        f"{in_bullets_pct:.0f}% of your skills also appear inside achievement bullets. Recruiters trust skills they see in context.",
    ))

    stuffed = [s for s in parsed_skills if lower.count(s.lower()) > 8]
    checks.append(_check(
        "no_keyword_stuffing", "skills", "No keyword stuffing",
        "fail" if stuffed else "pass",
        (
            f"Repeated excessively: {', '.join(stuffed)}. Modern ATS and recruiters penalise stuffing."
            if stuffed else
            "No skill is repeated to a stuffing level."
        ),
    ))

    # ── Group: length_format ────────────────────────────────────────────────
    if 300 <= word_count <= 1200:
        wc_status = "pass"
    elif 200 <= word_count <= 1600:
        wc_status = "warn"
    else:
        wc_status = "fail"
    checks.append(_check(
        "word_count", "length_format", "Length in the 1–2 page range",
        wc_status,
        f"{word_count} words. Roughly 300–1,200 words (≈1–2 pages) is the range ATS and recruiters handle best.",
        weight=2,
    ))

    checks.append(_check(
        "dates_present", "length_format", "Dates present for roles",
        "pass" if YEAR_RE.search(text) else "warn",
        "No year found. Dates anchor your experience timeline for parsers computing years of experience.",
    ))

    upper_words = [w for w in words if len(w) > 2 and w.isupper()]
    upper_pct = (len(upper_words) / word_count * 100) if word_count else 0
    checks.append(_check(
        "not_all_caps", "length_format", "Not written in ALL CAPS",
        _band(upper_pct, 20, 40, invert=True),
        f"{upper_pct:.0f}% of words are ALL-CAPS. Heavy caps hurt both parsing and readability.",
    ))

    # ── Scoring: weighted mean of checks; per-group means alongside ─────────
    total_weight = sum(c["weight"] for c in checks)
    score = sum(STATUS_VALUE[c["status"]] * c["weight"] for c in checks) / total_weight * 100

    groups: dict[str, float] = {}
    for group in ("file_parse", "contact", "sections", "content", "skills", "length_format"):
        members = [c for c in checks if c["group"] == group]
        w = sum(c["weight"] for c in members)
        groups[group] = sum(STATUS_VALUE[c["status"]] * c["weight"] for c in members) / w * 100

    return {
        "score": round(score, 1),
        "groups": {k: round(v, 1) for k, v in groups.items()},
        "checks": checks,
        "word_count": word_count,
        "skills_found": parsed_skills,
    }
