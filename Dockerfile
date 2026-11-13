# AI Resume & Job Matcher — FastAPI backend image
# Used by both the `api` and `worker` compose services (same image, different commands).
# Why python:3.12-slim: matches the locally verified Python 3.12 runtime, and the slim
# variant keeps the (already large, torch-carrying) image as small as possible.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System libraries: libpq for psycopg2/asyncpg wheels' runtime, curl for healthchecks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Default command is the API; the worker service overrides it in docker-compose.yml.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
