# AI Resume & Job Matcher — Project Specification

## 1. What this project is

A backend service that takes a resume and a job description, and returns:
- A **match score** (how well the resume fits the job)
- A list of **missing keywords/skills**
- **AI-generated suggestions** to improve the resume for that specific job

This is essentially your own ATS (Applicant Tracking System) simulator, built as a proper backend service — not a script. The goal is to demonstrate real backend engineering (APIs, databases, caching, async work) with an AI feature layered on top, not to build an AI research project.

**Why this project works well for job applications:** it uses FastAPI, PostgreSQL, Redis, and an AI/embeddings pipeline — which covers almost every keyword in typical "Python Backend Developer" job descriptions, and it's a project you can explain in depth because you'll have lived through building it.

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API framework | **FastAPI** | Async support, auto docs (Swagger), Pydantic validation |
| Database | **PostgreSQL** | Relational data: users, resumes, jobs, match history |
| Vector search | **pgvector** (Postgres extension) | Store resume/job embeddings, do similarity search directly in Postgres — no separate vector DB needed |
| Caching / rate limiting | **Redis** | Cache repeated match results, rate-limit the API, store background job status |
| Background tasks | **Celery** (broker: Redis) | Resume parsing + embedding generation can be slow — do it async, not inline in the request |
| ORM | **SQLAlchemy** (+ Alembic for migrations) | Standard, works well with FastAPI |
| Auth | **JWT** (via `python-jose` or `fastapi-users`) | Users log in, save resumes, see match history |
| Resume parsing | **pdfplumber** / **PyPDF2** (PDF), **python-docx** (Word) | Extract raw text from uploaded resumes |
| Embeddings | **Sentence-Transformers** (`all-MiniLM-L6-v2`, free/local) or **OpenAI Embeddings API** | Convert resume/job text into vectors for semantic comparison |
| AI feedback | **OpenAI API** / **Anthropic API** / **Groq** (any LLM API) | Generate human-readable suggestions ("add a quantified metric to bullet 2") |
| Containerization | **Docker + Docker Compose** | Run Postgres, Redis, API, and Celery worker together with one command |
| Deployment | **Render / Railway** (backend), **Vercel** (if you keep a frontend) | Free-tier friendly hosting |

> **Note on embeddings:** Use Sentence-Transformers locally first (free, no API key needed, good enough accuracy). Only add OpenAI/Groq for the "AI suggestions" text generation step, since that needs actual language generation, not just similarity scoring.

---

## 3. High-Level Architecture

```
                    ┌─────────────────────┐
                    │      Client          │
                    │ (Swagger UI / curl /  │
                    │  simple frontend)     │
                    └──────────┬───────────┘
                               │ REST API
                    ┌──────────▼───────────┐
                    │      FastAPI App      │
                    │  (routes + auth +     │
                    │   validation)         │
                    └──────┬───────┬────────┘
                           │       │
              ┌────────────┘       └─────────────┐
              ▼                                   ▼
    ┌──────────────────┐               ┌────────────────────┐
    │   PostgreSQL       │               │       Redis          │
    │ (+ pgvector ext.)  │               │ (cache + rate limit  │
    │ users, resumes,    │               │  + Celery broker)    │
    │ jobs, embeddings,  │               └──────────┬──────────┘
    │ match_results      │                          │
    └──────────────────┘               ┌────────────▼──────────┐
                                        │   Celery Worker         │
                                        │ - parse resume file      │
                                        │ - generate embeddings    │
                                        │ - call LLM for feedback  │
                                        └──────────────────────────┘
```

**Flow for a match request:**
1. User uploads resume (PDF) + pastes/uploads job description → `POST /resumes` and `POST /jobs`
2. API saves raw text, kicks off a **background Celery task** to parse + embed both
3. Once embeddings are ready, `POST /match/{resume_id}/{job_id}` computes cosine similarity (via pgvector's `<=>` operator) → gets a numeric match score
4. Keyword-diff logic (simple set comparison of extracted skills) → list of missing keywords
5. Optionally, call an LLM with resume + job + gaps → generate 3–5 specific improvement suggestions
6. Result is cached in Redis (so re-requesting the same resume/job pair is instant) and stored in Postgres for history

---

## 4. Core Features (build these first)

- [ ] **User auth** — register/login, JWT tokens
- [ ] **Resume upload** — accept PDF, extract raw text, store in DB
- [ ] **Job description input** — paste text or upload, store in DB
- [ ] **Text parsing** — extract sections (skills, experience, education) using simple rules/regex, or a lightweight NLP library (spaCy)
- [ ] **Embedding generation** — convert resume text and job description text into vectors (background task)
- [ ] **Similarity scoring** — cosine similarity between resume and job embeddings using pgvector → percentage match score
- [ ] **Keyword gap analysis** — extract a skills/keywords list from both texts, diff them, return "missing keywords"
- [ ] **Match history** — store every match result per user, list past matches via `GET /matches`
- [ ] **Rate limiting** — Redis-based, e.g. 10 match requests/minute per user

## 5. AI Features (the differentiator)

- [ ] **LLM-generated feedback** — given resume + job + gaps, ask an LLM to generate specific, actionable bullet-point rewrites (not generic advice)
- [ ] **Section-level scoring** — separately score "skills match," "experience relevance," and "keyword density" instead of one blended number
- [ ] **Resume rewrite suggestions** — LLM rewrites a weak bullet point into a stronger, quantified version
- [ ] **Job recommendation** (stretch) — given a resume, search across multiple stored job descriptions and rank them by similarity (this is where pgvector really shines — `ORDER BY embedding <=> query_embedding LIMIT 5`)

## 6. Nice-to-Have / Stretch Features

- [ ] Support DOCX resumes in addition to PDF
- [ ] Async endpoint that streams the LLM feedback token-by-token (shows off FastAPI's async streaming)
- [ ] Simple analytics: average match score improvement over multiple resume versions for the same job
- [ ] Export the AI feedback report as a PDF
- [ ] Dockerize fully with `docker-compose up` as the only setup step
- [ ] CI pipeline (GitHub Actions) running tests on every push

---

## 7. Database Schema (draft)

```sql
-- users
users (
  id SERIAL PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  hashed_password VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

-- resumes
resumes (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  raw_text TEXT NOT NULL,
  file_name VARCHAR,
  embedding VECTOR(384),   -- 384 dims if using all-MiniLM-L6-v2
  parsed_skills TEXT[],    -- extracted skill keywords
  created_at TIMESTAMP DEFAULT now()
);

-- job_descriptions
job_descriptions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  raw_text TEXT NOT NULL,
  title VARCHAR,
  company VARCHAR,
  embedding VECTOR(384),
  parsed_skills TEXT[],
  created_at TIMESTAMP DEFAULT now()
);

-- match_results
match_results (
  id SERIAL PRIMARY KEY,
  resume_id INT REFERENCES resumes(id),
  job_id INT REFERENCES job_descriptions(id),
  similarity_score FLOAT,
  missing_keywords TEXT[],
  ai_feedback TEXT,
  created_at TIMESTAMP DEFAULT now()
);
```

To enable pgvector: `CREATE EXTENSION IF NOT EXISTS vector;` then create an index for fast search: `CREATE INDEX ON resumes USING ivfflat (embedding vector_cosine_ops);`

---

## 8. API Endpoints (draft)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| POST | `/resumes` | Upload resume (PDF), triggers parsing + embedding task |
| GET | `/resumes/{id}` | Get parsed resume details |
| POST | `/jobs` | Submit a job description, triggers embedding task |
| GET | `/jobs/{id}` | Get job description details |
| POST | `/match/{resume_id}/{job_id}` | Run match, return score + gaps + AI feedback |
| GET | `/matches` | List all past match results for the logged-in user |
| GET | `/matches/{id}` | Get one specific match result in detail |
| GET | `/jobs/{resume_id}/recommendations` | (Stretch) Rank all stored jobs by similarity to this resume |
| GET | `/health` | Health check for deployment |

---

## 9. The Matching Algorithm (how the score is actually computed)

1. **Parse** both texts into clean plain text (strip formatting, headers/footers).
2. **Extract skills/keywords** — either a curated skill dictionary (fast, simple) or an LLM call that extracts structured skills as JSON (more accurate, costs an API call).
3. **Embed** both texts using Sentence-Transformers → get two 384-dim vectors.
4. **Compute cosine similarity** between the vectors → a 0–1 score → convert to a percentage. This captures *semantic* similarity (so "led a team" matches "managed a team" even without exact keyword overlap).
5. **Compute keyword overlap** separately — what % of the job's required skills appear in the resume. This is more literal and closer to how real ATS systems filter.
6. **Combine both scores** (e.g., 60% semantic + 40% keyword overlap) into a final match percentage — and show both sub-scores separately, since that's more honest and more useful than one blended number.
7. **Generate feedback**: send the resume text, job text, and the specific missing keywords to an LLM with a prompt like: *"Given this resume and this job description, suggest 3 specific, quantifiable rewrites to existing bullet points that would improve the match. Do not invent experience the candidate doesn't have."*

---

## 10. Build Order (so it's demoable at every stage)

1. FastAPI project skeleton + Postgres connection + Alembic migrations
2. User auth (register/login/JWT)
3. Resume upload endpoint + PDF text extraction (synchronous first, no Celery yet)
4. Job description endpoint
5. Add Sentence-Transformers embedding generation, store vectors in pgvector
6. Build the `/match` endpoint using cosine similarity — **this is your first real demo**
7. Add keyword extraction + gap analysis
8. Add Redis caching for repeated match requests
9. Move parsing + embedding into Celery background tasks (shows async/background task skills explicitly)
10. Add LLM-based feedback generation
11. Add rate limiting via Redis
12. Dockerize everything, write a clear README
13. (Stretch) Add job recommendation endpoint using pgvector's nearest-neighbor search across multiple jobs

---

## 11. What to Put in the README (for recruiters skimming GitHub)

- One-paragraph summary of what it does and why you built it
- Architecture diagram (copy the one above or redraw it)
- Tech stack list
- Setup instructions (`docker-compose up` should be the whole story)
- A few screenshots of the Swagger UI (`/docs`) showing real requests/responses
- One example: a real resume snippet + job description + the actual match score and AI feedback it produced

---

## 12. Resume Bullet Points (once built)

Draft versions to adapt once you've actually built it and have real numbers:

- Built a full-stack AI resume-matching platform using FastAPI, PostgreSQL (pgvector), and Redis, computing semantic similarity between resumes and job descriptions using Sentence-Transformer embeddings.
- Designed and implemented background task processing with Celery and Redis to handle resume parsing and embedding generation asynchronously, reducing API response time from Xs to Yms.
- Integrated an LLM-based feedback pipeline that generates specific, actionable resume improvement suggestions based on job description gap analysis.
- Implemented Redis-based caching and rate limiting on match endpoints to reduce redundant computation and protect against abuse.

Fill in the X/Y once you have real before/after numbers — a concrete number here is worth more than the whole rest of the bullet.
