"""Resume document helpers (Phase 13 — builder).

Two pure functions, both unit-testable without infrastructure:

- `flatten_content_to_text(content)`: renders the structured document JSON to
  the plain text the rest of the product understands (embeddings, ATS checks,
  matching). This is the bridge that makes built resumes first-class citizens
  of the existing pipeline (decisions.md §13.2). The section headings it emits
  are deliberately the standard words the ATS section checks look for.

- `parse_text_to_content(raw_text)`: the reverse direction for "import an
  existing resume" — a deterministic heading-based splitter that turns
  extracted text into a draft document. It is a heuristic, and the result is
  always a draft the user reviews in the editor (decisions.md §13.4); LLM
  structured extraction is a Phase 5 upgrade.
"""

import re

# ── Content schema (v1) ─────────────────────────────────────────────────────
# {
#   "personal": {"full_name": str, "title": str, "email": str, "phone": str,
#                "location": str, "links": [str]},
#   "summary": str,
#   "experience": [{"role": str, "company": str, "location": str,
#                   "start": str, "end": str, "current": bool,
#                   "bullets": [str]}],
#   "education": [{"school": str, "degree": str, "field": str,
#                  "start": str, "end": str}],
#   "skills": {"groups": [{"label": str, "items": [str]}]},
#   "projects": [{"name": str, "description": str, "bullets": [str]}],
#   "certifications": [str],
#   "languages": [str],
#   "custom_sections": [{"title": str, "items": [str]}]
# }

EMPTY_CONTENT: dict = {
    "personal": {
        "full_name": "", "title": "", "email": "", "phone": "",
        "location": "", "links": [],
    },
    "summary": "",
    "experience": [],
    "education": [],
    "skills": {"groups": []},
    "projects": [],
    "certifications": [],
    "languages": [],
    "custom_sections": [],
}

TEMPLATES = ["classic", "modern", "compact-tech", "sidebar", "minimal", "graduate"]


def _clean_lines(items) -> list[str]:
    return [str(i).strip() for i in (items or []) if str(i).strip()]


def flatten_content_to_text(content: dict) -> str:
    """Render structured document content to pipeline plain text."""
    content = content or {}
    parts: list[str] = []

    personal = content.get("personal") or {}
    header = [personal.get("full_name", ""), personal.get("title", "")]
    contact = [
        personal.get("email", ""), personal.get("phone", ""),
        personal.get("location", ""),
    ] + _clean_lines(personal.get("links"))
    header_block = "\n".join(x for x in header if x and str(x).strip())
    contact_line = " | ".join(str(x) for x in contact if x and str(x).strip())
    if header_block:
        parts.append(header_block)
    if contact_line:
        parts.append(contact_line)

    summary = (content.get("summary") or "").strip()
    if summary:
        parts.append(f"Summary\n{summary}")

    experience = content.get("experience") or []
    if experience:
        lines = ["Experience"]
        for job in experience:
            role = job.get("role", "")
            company = job.get("company", "")
            dates = " - ".join(
                x for x in [job.get("start", ""), "Present" if job.get("current") else job.get("end", "")] if x
            )
            heading = " — ".join(x for x in [role, company] if x)
            if dates:
                heading = f"{heading} ({dates})" if heading else dates
            if heading:
                lines.append(heading)
            for bullet in _clean_lines(job.get("bullets")):
                lines.append(f"• {bullet}")
        parts.append("\n".join(lines))

    skills = (content.get("skills") or {}).get("groups") or []
    if skills:
        lines = ["Skills"]
        for group in skills:
            items = _clean_lines(group.get("items"))
            if not items:
                continue
            label = group.get("label", "")
            lines.append(f"{label}: {', '.join(items)}" if label else ", ".join(items))
        if len(lines) > 1:
            parts.append("\n".join(lines))

    projects = content.get("projects") or []
    if projects:
        lines = ["Projects"]
        for project in projects:
            if project.get("name"):
                lines.append(project["name"])
            if project.get("description"):
                lines.append(project["description"])
            for bullet in _clean_lines(project.get("bullets")):
                lines.append(f"• {bullet}")
        parts.append("\n".join(lines))

    education = content.get("education") or []
    if education:
        lines = ["Education"]
        for edu in education:
            bits = [edu.get("degree", ""), edu.get("field", ""), edu.get("school", "")]
            line = ", ".join(x for x in bits if x)
            dates = " - ".join(x for x in [edu.get("start", ""), edu.get("end", "")] if x)
            if dates:
                line = f"{line} ({dates})" if line else dates
            if line:
                lines.append(line)
        parts.append("\n".join(lines))

    for key, heading in (("certifications", "Certifications"), ("languages", "Languages")):
        items = _clean_lines(content.get(key))
        if items:
            parts.append(f"{heading}\n" + ", ".join(items))

    for section in content.get("custom_sections") or []:
        items = _clean_lines(section.get("items"))
        if section.get("title") and items:
            parts.append(section["title"] + "\n" + "\n".join(f"• {i}" for i in items))

    return "\n\n".join(parts)


# ── Heuristic import: extracted text → draft document ──────────────────────

_HEADING_MAP = [
    (re.compile(r"^(professional\s+)?summary$|^profile$|^objective$|^about(\s+me)?$", re.I), "summary"),
    (re.compile(r"^(work\s+|professional\s+)?experience$|^employment(\s+history)?$", re.I), "experience"),
    (re.compile(r"^education(al)?(\s+background)?$|^qualifications$", re.I), "education"),
    (re.compile(r"^(technical\s+)?skills$|^technologies$|^tech\s+stack$|^core\s+competencies$", re.I), "skills"),
    (re.compile(r"^projects?$", re.I), "projects"),
    (re.compile(r"^certifications?$|^certificates$|^licenses$", re.I), "certifications"),
    (re.compile(r"^languages$", re.I), "languages"),
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(\+\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
_LINK_RE = re.compile(r"(https?://[^\s|]+|linkedin\.com/[^\s|]+|github\.com/[^\s|]+)")
_YEAR_RANGE_RE = re.compile(r"((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2}|present|current)", re.I)


def _match_heading(line: str) -> str | None:
    candidate = line.strip().strip(":").strip()
    if len(candidate) > 40:
        return None
    for pattern, key in _HEADING_MAP:
        if pattern.match(candidate):
            return key
    return None


def parse_text_to_content(raw_text: str) -> dict:
    """Split extracted resume text into a draft document (best-effort).

    Lines before the first recognised heading become the personal block
    (name = first line, email/phone/links detected by pattern, leftover lines
    seed the summary if no summary section exists).
    """
    content = {
        "personal": {"full_name": "", "title": "", "email": "", "phone": "", "location": "", "links": []},
        "summary": "", "experience": [], "education": [],
        "skills": {"groups": []}, "projects": [],
        "certifications": [], "languages": [], "custom_sections": [],
    }
    lines = [ln.rstrip() for ln in (raw_text or "").splitlines()]
    buckets: dict[str, list[str]] = {"__head__": []}
    current = "__head__"
    for line in lines:
        heading = _match_heading(line) if line.strip() else None
        if heading:
            current = heading
            buckets.setdefault(current, [])
            continue
        buckets.setdefault(current, []).append(line)

    head_lines = [ln.strip() for ln in buckets.get("__head__", []) if ln.strip()]
    if head_lines:
        content["personal"]["full_name"] = head_lines[0]
        rest = head_lines[1:]
        if rest:
            content["personal"]["title"] = rest[0]
        joined_head = " ".join(head_lines)
        email = _EMAIL_RE.search(joined_head)
        if email:
            content["personal"]["email"] = email.group(0)
        phone = _PHONE_RE.search(joined_head)
        if phone:
            content["personal"]["phone"] = phone.group(0)
        content["personal"]["links"] = _LINK_RE.findall(joined_head)

    def bucket_text(key: str) -> list[str]:
        return [ln.strip() for ln in buckets.get(key, []) if ln.strip()]

    summary_lines = bucket_text("summary")
    if summary_lines:
        content["summary"] = " ".join(summary_lines)

    # Experience: each entry starts at a line containing a year range.
    exp_entries: list[dict] = []
    current_entry: dict | None = None
    for line in bucket_text("experience"):
        years = _YEAR_RANGE_RE.search(line)
        is_bullet = line.startswith(("•", "-", "*", "▪", "◦", "·", "–"))
        if years and not is_bullet:
            heading_text = re.sub(r"\(\s*\)", "", _YEAR_RANGE_RE.sub("", line)).strip(" ,|—-")
            role, _, company = heading_text.partition("—")
            if not company:
                role, _, company = heading_text.partition(" at ")
            if not company:
                role, _, company = heading_text.partition(",")
            current_entry = {
                "role": role.strip(), "company": company.strip(), "location": "",
                "start": years.group(1),
                "end": "" if years.group(2).lower() in ("present", "current") else years.group(2),
                "current": years.group(2).lower() in ("present", "current"),
                "bullets": [],
            }
            exp_entries.append(current_entry)
        elif current_entry is not None:
            if is_bullet:
                current_entry["bullets"].append(line.lstrip("•-*▪◦·– ").strip())
            elif line:
                current_entry["bullets"].append(line)
    content["experience"] = exp_entries

    edu_entries = []
    for line in bucket_text("education"):
        years = _YEAR_RANGE_RE.search(line)
        text = re.sub(r"\(\s*\)", "", _YEAR_RANGE_RE.sub("", line)).strip(" ,|()—-")
        if not text:
            continue
        parts = [p.strip() for p in text.split(",") if p.strip()]
        edu_entries.append({
            "school": parts[-1] if parts else "",
            "degree": parts[0] if parts else "",
            "field": parts[1] if len(parts) > 2 else "",
            "start": years.group(1) if years else "",
            "end": years.group(2) if years and years.group(2).lower() not in ("present", "current") else "",
        })
    content["education"] = edu_entries

    skill_items: list[str] = []
    for line in bucket_text("skills"):
        _, _, rest = line.partition(":")
        chunk = rest if rest else line
        skill_items.extend(s.strip() for s in re.split(r"[,|•·]", chunk) if s.strip())
    if skill_items:
        content["skills"] = {"groups": [{"label": "Skills", "items": skill_items}]}

    project_entries = []
    for line in bucket_text("projects"):
        if line.startswith(("•", "-", "*", "▪", "◦", "·", "–")):
            if project_entries:
                project_entries[-1]["bullets"].append(line.lstrip("•-*▪◦·– ").strip())
        else:
            project_entries.append({"name": line, "description": "", "bullets": []})
    content["projects"] = project_entries

    for key in ("certifications", "languages"):
        items = []
        for line in bucket_text(key):
            items.extend(
                s.strip().lstrip("•-*▪◦·– ").strip()
                for s in re.split(r"[,|]", line) if s.strip()
            )
        content[key] = items

    return content
