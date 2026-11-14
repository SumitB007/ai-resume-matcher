"""Unit tests for the builder's document service (Phase 13).

Pure functions only: flattening (document → pipeline text) and the heuristic
import parser (extracted text → draft document). No DB, no network.
"""

from app.services.document_service import flatten_content_to_text, parse_text_to_content

CONTENT = {
    "personal": {
        "full_name": "Jane Developer", "title": "Senior Backend Developer",
        "email": "jane@example.com", "phone": "+1 555-123-4567",
        "location": "Remote", "links": ["linkedin.com/in/janedev"],
    },
    "summary": "Backend developer with 6 years of experience.",
    "experience": [{
        "role": "Senior Backend Developer", "company": "TechCorp", "location": "",
        "start": "2021", "end": "", "current": True,
        "bullets": ["Built a FastAPI platform serving 2M requests per day", "Reduced latency by 45%"],
    }],
    "education": [{
        "school": "State University", "degree": "B.Tech", "field": "Computer Science",
        "start": "2015", "end": "2019",
    }],
    "skills": {"groups": [{"label": "Backend", "items": ["Python", "FastAPI", "PostgreSQL"]}]},
    "projects": [{"name": "Matcher", "description": "Resume tool", "bullets": ["Shipped v1"]}],
    "certifications": ["AWS Certified Developer"],
    "languages": ["English", "Hindi"],
    "custom_sections": [],
}

UPLOAD_TEXT = """Jane Developer
Senior Backend Developer
jane@example.com | +1 555-123-4567 | linkedin.com/in/janedev

Summary
Backend developer with 6 years of experience building Python APIs.

Experience
Senior Backend Developer — TechCorp (2021 - Present)
• Built a FastAPI platform serving 2M requests per day
• Reduced latency by 45% with Redis caching

Skills
Python, FastAPI, PostgreSQL, Redis, Docker

Education
B.Tech, Computer Science, State University (2015 - 2019)
"""


def test_flatten_has_standard_headings_and_content():
    text = flatten_content_to_text(CONTENT)
    assert "Jane Developer" in text
    assert "jane@example.com" in text
    assert "\nSummary\n" in text
    assert "\nExperience\n" in text
    assert "• Built a FastAPI platform" in text
    assert "(2021 - Present)" in text
    assert "\nSkills\n" in text
    assert "Backend: Python, FastAPI, PostgreSQL" in text
    assert "\nEducation\n" in text
    assert "Certifications" in text


def test_flatten_empty_content_is_harmless():
    assert flatten_content_to_text({}) == ""
    assert flatten_content_to_text(None) == ""


def test_import_parses_personal_and_sections():
    content = parse_text_to_content(UPLOAD_TEXT)
    assert content["personal"]["full_name"] == "Jane Developer"
    assert content["personal"]["email"] == "jane@example.com"
    assert "6 years of experience" in content["summary"]
    assert len(content["experience"]) == 1
    entry = content["experience"][0]
    assert entry["role"] == "Senior Backend Developer"
    assert entry["company"] == "TechCorp"
    assert entry["current"] is True
    assert len(entry["bullets"]) == 2
    skills = content["skills"]["groups"][0]["items"]
    assert "Python" in skills and "Docker" in skills
    assert len(content["education"]) == 1


def test_flatten_of_import_keeps_key_facts():
    text = flatten_content_to_text(parse_text_to_content(UPLOAD_TEXT))
    assert "Jane Developer" in text
    assert "FastAPI" in text
    assert "Experience" in text
