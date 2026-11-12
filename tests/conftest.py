"""Pytest configuration and shared fixtures.

Will be expanded with database fixtures and test client in later phases.
"""

import pytest


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
    John Doe
    Senior Python Developer
    john.doe@email.com | (555) 123-4567

    SUMMARY
    Experienced Python developer with 5+ years building scalable backend services
    using FastAPI, Django, and Flask. Strong background in database design,
    API development, and cloud deployment.

    SKILLS
    Python, FastAPI, Django, Flask, PostgreSQL, Redis, Docker, Kubernetes,
    AWS, Git, REST API, SQLAlchemy, Celery, pytest, CI/CD

    EXPERIENCE
    Senior Backend Developer | Acme Corp | 2021-Present
    - Designed and implemented RESTful APIs using FastAPI serving 10K+ requests/day
    - Optimized PostgreSQL queries reducing response times by 40%
    - Built background task processing with Celery and Redis
    - Implemented CI/CD pipelines using GitHub Actions

    Backend Developer | StartupXYZ | 2019-2021
    - Developed microservices architecture using Python and Docker
    - Managed PostgreSQL and Redis databases in production
    - Wrote comprehensive unit and integration tests with pytest

    EDUCATION
    B.S. Computer Science | State University | 2019
    """


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Senior Python Backend Developer

    Company: TechCorp Inc.
    Location: Remote

    We are looking for a Senior Python Backend Developer to join our team.

    Requirements:
    - 5+ years of experience with Python
    - Strong experience with FastAPI or Django
    - PostgreSQL and database design expertise
    - Experience with Redis for caching and message queuing
    - Docker and Kubernetes knowledge
    - Familiarity with CI/CD pipelines
    - Experience with AWS or GCP
    - Strong understanding of RESTful API design
    - Experience with async programming
    - Unit testing with pytest

    Nice to have:
    - Experience with machine learning / NLP
    - GraphQL experience
    - Terraform for infrastructure as code
    - Experience with Kafka or RabbitMQ
    """


@pytest.fixture
def test_user_id():
    """Ensure a test user exists and return their user ID."""
    from app.database import get_sync_db
    from app.models.user import User
    from app.core.security import hash_password

    with get_sync_db() as session:
        user = session.query(User).filter(User.email == "test@example.com").first()
        if not user:
            user = User(
                email="test@example.com",
                hashed_password=hash_password("password123"),
            )
            session.add(user)
            session.flush()
        return user.id


@pytest.fixture(autouse=True)
def cleanup_async_db():
    """Ensure async database connection pool is disposed after each test."""
    yield
    import asyncio
    from app.database import engine

    try:
        asyncio.run(engine.dispose())
    except Exception:
        pass



