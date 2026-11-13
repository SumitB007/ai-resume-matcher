# System Architecture & Execution Flow Guide
## AI Resume & Job Matcher Platform

This document provides a comprehensive, end-to-end operational guide explaining **how the application executes**, its **entry point**, the **runtime lifecycle**, and the exact **call hierarchy ("what calls what")** across all features.

---

## Table of Contents
1. [System Topology & Infrastructure Overview](#1-system-topology--infrastructure-overview)
2. [Application Entry Point & Bootstrapping](#2-application-entry-point--bootstrapping)
3. [Process Architecture](#3-process-architecture)
4. [Detailed Execution Flows](#4-detailed-execution-flows)
   - [Flow 1: User Authentication & Security Pipeline](#flow-1-user-authentication--security-pipeline)
   - [Flow 2: Resume Ingestion & Asynchronous Embedding Pipeline](#flow-2-resume-ingestion--asynchronous-embedding-pipeline)
   - [Flow 3: Job Description Ingestion Pipeline](#flow-3-job-description-ingestion-pipeline)
   - [Flow 4: Core Resume ↔ Job Match Pipeline](#flow-4-core-resume--job-match-pipeline)
   - [Flow 5: Real-Time Server-Sent Events (SSE) Streaming Pipeline](#flow-5-real-time-server-sent-events-sse-streaming-pipeline)
   - [Flow 6: Nearest-Neighbor Job Recommendations Pipeline](#flow-6-nearest-neighbor-job-recommendations-pipeline)
   - [Flow 7: Resume Version Progression & ATS Analytics Pipeline](#flow-7-resume-version-progression--ats-analytics-pipeline)
   - [Flow 8: Downloadable PDF Assessment Report Generation](#flow-8-downloadable-pdf-assessment-report-generation)
   - [Flow 9: Frontend Authentication via BFF Proxy (Phase 11)](#flow-9-frontend-authentication-via-bff-proxy-phase-11)
   - [Flow 10: Frontend Matcher Workspace (Phase 11)](#flow-10-frontend-matcher-workspace-phase-11)
5. [What Calls What: Component Call Tree Matrix](#5-what-calls-what-component-call-tree-matrix)

---

## 1. System Topology & Infrastructure Overview

```
                          ┌───────────────────────────┐
                          │   Client / Web Browser    │
                          │   (Swagger UI / API User) │
                          └─────────────┬─────────────┘
                                        │ HTTP / REST / SSE
                                        ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI ASGI Application (Uvicorn Server on Port 8000)                             │
│                                                                                   │
│  app/main.py ──► CORS Middleware ──► Global Exception Handlers                   │
│         │                                                                         │
│         └──► Root API Router (app/api/__init__.py)                                │
│               ├── /auth        (app/api/auth.py)                                  │
│               ├── /resumes     (app/api/resumes.py)                               │
│               ├── /jobs        (app/api/jobs.py)                                  │
│               ├── /match       (app/api/matches.py)                               │
│               ├── /tasks       (app/api/tasks.py)                                 │
│               ├── /ai          (app/api/ai.py)                                    │
│               └── /analytics   (app/api/analytics.py)                             │
└───────────┬───────────────────────────┬───────────────────────────┬───────────────┘
            │                           │                           │
            │ Async SQLAlchemy          │ Async Redis Client        │ Celery Task Dispatch
            │ (asyncpg)                 │ (redis-py)                │ (.delay())
            ▼                           ▼                           ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────────┐
│ PostgreSQL 16+        │   │ Redis (Port 6379)     │   │ Celery Worker Process     │
│ with pgvector         │   │                       │   │ (--pool=solo)             │
│                       │   │ DB 0: Cache & Limiter │   │                           │
│ • users               │   │ DB 1: Celery Broker   │◄──┤ app/tasks/celery_app.py   │
│ • resumes (VECTOR)    │   │ DB 2: Celery Results  │   │ • resume_tasks.py         │
│ • job_desc (VECTOR)   │   └───────────────────────┘   │ • embedding_tasks.py      │
│ • match_results       │                               │ • llm_tasks.py            │
└───────────────────────┘                               └─────────────┬─────────────┘
            ▲                                                         │
            │                  Sync SQLAlchemy (psycopg2)             │
            └─────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTPS External API
                                        ▼
                            ┌───────────────────────┐
                            │ OpenRouter AI Gateway │
                            │ (https://openrouter)  │
                            │ Mistral, Llama, GPT   │
                            └───────────────────────┘
```

---

## 2. Application Entry Point & Bootstrapping

### Entry Point File: `app/main.py`
When the Uvicorn ASGI server boots (`uvicorn app.main:app`), the execution order is:

1. **Configuration Loading (`app/config.py`):**
   * Pydantic `Settings` parses environment variables from `.env` (Database URLs, Redis URLs, Secret keys, OpenRouter settings).
2. **FastAPI Instance Creation:**
   * Initialized with metadata (`title`, `version`, `docs_url="/docs"`).
3. **Lifespan Context Manager (`lifespan` in `app/main.py`):**
   * Triggers on server startup:
     ```python
     @asynccontextmanager
     async def lifespan(app: FastAPI):
         # Startup: Print diagnostics, verify DB configuration
         yield
         # Shutdown: Cleanly close pools and connections
     ```
4. **Middleware Registration:**
   * `CORSMiddleware` configured to allow cross-origin client requests.
5. **Router Mounting (`app/api/__init__.py`):**
   * Sub-routers are aggregated under `api_router` and registered with the main app.
6. **Centralized Exception Handler Attachment:**
   * Handlers for `RequestValidationError`, `HTTPException`, and generic `Exception` attached to guarantee consistent JSON error structures.

---

## 3. Process Architecture

The system operates across **two distinct application runtimes**:

| Component | Technology | Concurrency Model | Responsibility |
|---|---|---|---|
| **Web API Service** | FastAPI + Uvicorn | Asyncio Event Loop | Non-blocking HTTP request handling, JWT verification, Redis cache lookups, database I/O, SSE streaming. |
| **Worker Service** | Celery 5.6 | Dedicated Process (`--pool=solo`) | CPU-heavy text extraction, Sentence-Transformers embedding inference, batch vectorization. |

---

## 4. Detailed Execution Flows

### Flow 1: User Authentication & Security Pipeline
```
[Client] ──► POST /auth/register ──► app/api/auth.py (register)
                                          │
                                          ├──► app/core/security.py (hash_password)
                                          │         └──► bcrypt.hashpw()
                                          └──► INSERT INTO users ──► 201 Created

[Client] ──► POST /auth/login ──► app/api/auth.py (login)
                                       │
                                       ├──► SELECT * FROM users WHERE email = :email
                                       ├──► app/core/security.py (verify_password)
                                       └──► app/core/security.py (create_access_token)
                                                 └──► jwt.encode(payload, SECRET_KEY)
                                                 └──► Returns {"access_token": "...", "token_type": "bearer"}
```
* **Protected Routes:** Downstream routes inject `current_user: User = Depends(get_current_user)`.
* `app/core/dependencies.py` extracts the `Authorization: Bearer <token>` header, decodes the JWT with `jwt.decode()`, extracts the `user_id`, and queries the user record in PostgreSQL.

---

### Flow 2: Resume Ingestion & Asynchronous Embedding Pipeline
```
[Client] ──► POST /resumes (Multipart File Upload: PDF or DOCX)
                  │
                  ▼
         [app/api/resumes.py: upload_resume()]
                  │
                  ├── 1. Validate file extension (.pdf, .docx) & file size (<= 10MB)
                  ├── 2. Extract text:
                  │        • If PDF: app/utils/pdf_parser.py (extract_text_from_pdf via pdfplumber)
                  │        • If DOCX: app/utils/docx_parser.py (extract_text_from_docx via python-docx)
                  ├── 3. Parse skills: app/services/keyword_service.py (extract_skills)
                  ├── 4. Insert into PostgreSQL:
                  │        Resume(status="pending", raw_text=..., parsed_skills=...)
                  │        await db.commit()  <-- Guarantees DB row is visible to worker
                  ├── 5. Dispatch background task:
                  │        process_resume_task.delay(resume.id)
                  │        Update resume.task_id = task.id
                  │        await db.commit()
                  └── 6. Return HTTP 201 Created in ~300ms:
                           {"id": 1, "status": "pending", "task_id": "uuid-..."}
```

#### Background Celery Execution:
```
[Redis DB 1 (Broker)] ──► [Celery Worker Process]
                                 │
                                 ▼
         [app/tasks/resume_tasks.py: process_resume_task()]
                                 │
                                 ├── 1. self.update_state(state="PROCESSING", step="loading_resume")
                                 ├── 2. Query resume using get_sync_db() (psycopg2 sync connection)
                                 ├── 3. If skills missing: extract_skills(resume.raw_text)
                                 ├── 4. Generate 384-dimensional vector embedding:
                                 │        app/services/embedding_service.py (generate_embedding)
                                 │        └── SentenceTransformer('all-MiniLM-L6-v2').encode(text)
                                 ├── 5. Update PostgreSQL:
                                 │        resume.embedding = vector
                                 │        resume.status = "completed"
                                 │        session.commit()
                                 └── 6. Return task result: {"status": "completed", "embedding_dims": 384}
```

---

### Flow 3: Job Description Ingestion Pipeline
```
[Client] ──► POST /jobs (JSON: title, company, raw_text)
                  │
                  ▼
         [app/api/jobs.py: create_job()]
                  │
                  ├── 1. Extract technical skills: keyword_service.extract_skills(raw_text)
                  ├── 2. Insert into PostgreSQL: JobDescription(status="pending")
                  ├── 3. await db.commit()
                  ├── 4. Dispatch Celery task: process_job_task.delay(job.id)
                  └── 5. Return HTTP 201 Created with task_id
```

---

### Flow 4: Core Resume ↔ Job Match Pipeline
```
[Client] ──► POST /match/{resume_id}/{job_id}?generate_feedback=true&model=...
                  │
                  ▼
         [app/api/matches.py: run_match()]
                  │
                  ├── 1. Verify Ownership: Ensure resume & job belong to current_user
                  ├── 2. Rate Limiter: app/core/rate_limiter.py (check_rate_limit)
                  │        └── Redis DB 0: Check 10 req/min limit per user
                  ├── 3. Cache Check: app/services/cache_service.py (get_cached_match)
                  │        └── Redis DB 0: If match:{resume_id}:{job_id} exists, return cached result
                  ├── 4. Vector Verification: app/services/matching_service.py (ensure_embedding)
                  │        └── Generates on-the-fly if background task was skipped
                  ├── 5. Native pgvector Cosine Similarity:
                  │        SELECT 1 - ((SELECT embedding FROM resumes WHERE id = :r)
                  │                    <=>
                  │                    (SELECT embedding FROM job_descriptions WHERE id = :j))
                  ├── 6. Keyword Overlap & Skill Gaps:
                  │        app/services/keyword_service.py:
                  │        • compute_keyword_overlap(resume_skills, job_skills)
                  │        • find_missing_keywords(resume_skills, job_skills)
                  ├── 7. Blended Score Computation:
                  │        Overall Score = (0.6 * similarity_pct) + (0.4 * keyword_pct)
                  ├── 8. Section-Level Scoring:
                  │        compute_section_scores(resume_text, job_text, resume_skills, job_skills)
                  │        -> {"skills_match": X, "experience_relevance": Y, "keyword_density": Z}
                  ├── 9. Optional AI Feedback Generation:
                  │        app/services/llm_service.py (generate_match_feedback)
                  │        └── OpenRouter API call / Local fallback generator
                  ├── 10. Persist Result:
                  │        INSERT INTO match_results (...)
                  │        await db.commit()
                  ├── 11. Write to Cache:
                  │        app/services/cache_service.py (set_cached_match) -> 1-hour TTL
                  └── 12. Return MatchResponse (scores, section breakdown, gaps, AI feedback)
```

---

### Flow 5: Real-Time Server-Sent Events (SSE) Streaming Pipeline
```
[Client] ──► GET /matches/{match_id}/feedback/stream
                  │
                  ▼
         [app/api/matches.py: stream_match_feedback()]
                  │
                  ├── 1. Fetch match_result, resume, and job records
                  ├── 2. Construct targeted prompt containing resume, job, and missing skills
                  ├── 3. Open async stream: app/services/llm_service.py (stream_openrouter)
                  │        └── httpx.AsyncClient.stream("POST", openrouter_base_url)
                  └── 4. Return StreamingResponse(media_type="text/event-stream")
                           │
                           ├── Yield: data: {"token": "Based "}\n\n
                           ├── Yield: data: {"token": "on "}\n\n
                           ├── Yield: data: {"token": "your "}\n\n
                           └── Yield: data: [DONE]\n\n
                           (Accumulated feedback is saved to PostgreSQL match_results.ai_feedback)
```

---

### Flow 6: Nearest-Neighbor Job Recommendations Pipeline
```
[Client] ──► GET /jobs/{resume_id}/recommendations?limit=5&min_similarity=60
                  │
                  ▼
         [app/services/recommendation_service.py: get_job_recommendations_for_resume()]
                  │
                  ├── 1. Fetch resume and ensure embedding exists
                  ├── 2. Execute database-native pgvector nearest-neighbor search:
                  │        SELECT j.id, j.title, j.company, j.raw_text, j.parsed_skills,
                  │               1 - (j.embedding <=> r.embedding) AS similarity
                  │        FROM job_descriptions j, resumes r
                  │        WHERE r.id = :resume_id AND j.embedding IS NOT NULL
                  │          AND (1 - (j.embedding <=> r.embedding)) >= :min_sim
                  │        ORDER BY j.embedding <=> r.embedding ASC
                  │        LIMIT :limit OFFSET :offset;
                  ├── 3. For each ranked job:
                  │        • Calculate keyword overlap score
                  │        • Calculate matching skills and missing skills
                  │        • Compute blended overall score (60% semantic + 40% keyword)
                  └── 4. Return JobRecommendationsResponse (ranked recommendations list)
```

---

### Flow 7: Resume Version Progression & ATS Analytics Pipeline
```
[Client] ──► GET /analytics/resume-progress/{job_id}
                  │
                  ▼
         [app/services/analytics_service.py: get_resume_progress_for_job()]
                  │
                  ├── 1. Query all matches for current_user and target job_id:
                  │        SELECT match_results.*, resumes.file_name
                  │        FROM match_results JOIN resumes ON match_results.resume_id = resumes.id
                  │        WHERE job_id = :job_id AND user_id = :user_id
                  │        ORDER BY match_results.created_at ASC
                  ├── 2. Compute timeline metrics:
                  │        • Initial Score = match[0].overall_score
                  │        • Latest Score  = match[-1].overall_score
                  │        • Score Delta   = Latest Score - Initial Score
                  │        • Average Score = sum(scores) / count
                  ├── 3. Compute Skills Gained (Set Difference):
                  │        Skills Gained = match[0].missing_keywords - match[-1].missing_keywords
                  └── 4. Return ResumeProgressResponse (timeline, score progression, skills gained)
```

---

### Flow 8: Downloadable PDF Assessment Report Generation
```
[Client] ──► GET /matches/{match_id}/export-pdf
                  │
                  ▼
         [app/api/matches.py: export_match_pdf()]
                  │
                  ├── 1. Verify match ownership and retrieve associated resume and job
                  ├── 2. Call app/services/pdf_export_service.py (generate_match_report_pdf)
                  │        │
                  │        ├── Initialize in-memory BytesIO buffer
                  │        ├── Build ReportLab SimpleDocTemplate
                  │        ├── Render Header banner, Target Role, and Candidate metadata table
                  │        ├── Render 3-column Score Card (Overall, Semantic, Keyword)
                  │        ├── Render Section-Level Assessment Table
                  │        ├── Render Skills Gap Table (Matching Skills vs Missing Required Skills)
                  │        ├── Render Formatted AI Recommendations & Bullet Rewrites
                  │        └── doc.build(elements) -> buffer.getvalue()
                  └── 3. Return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
                                                  headers={"Content-Disposition": "attachment; filename=..."})
```

---


---

### Flow 9: Frontend Authentication via BFF Proxy (Phase 11)
```
[Browser] ──► POST /api/auth/login  (Next.js route handler, src/app/api/auth/login/route.ts)
                  │
                  ├── 1. Forward {email, password} ──► FastAPI POST /auth/login (API_INTERNAL_URL)
                  ├── 2. On 200: store returned JWT in httpOnly cookie `access_token`
                  │        (SameSite=Lax, 24h — browser JS can never read it)
                  └── 3. Return {ok: true} — the token itself is never sent to the client

[Browser] ──► any /api/backend/* request
                  │
                  ▼
         [src/app/api/backend/[...path]/route.ts]
                  ├── 1. Read `access_token` cookie (next/headers, server-side only)
                  ├── 2. No cookie ──► 401 envelope immediately (no backend call)
                  ├── 3. Attach Authorization: Bearer <token>, forward method/query/body
                  │        (uploads forwarded as raw bytes; response body streamed through,
                  │         so SSE and PDF downloads are never buffered)
                  └── 4. Backend status + error envelope pass through untouched

[Navigation] ──► src/proxy.ts (Next 16 Proxy, optimistic check only)
                  ├── /app/* without cookie ──► redirect /login?next=<path>
                  └── /login|/signup with cookie ──► redirect /app
         (Real validation stays at the data layer: a backend 401 surfaces via
          /api/auth/me, which also deletes the dead cookie.)
```

---

### Flow 10: Frontend Matcher Workspace (Phase 11)
```
[app/match/page.tsx] ──► upload resume (FormData) ──► /api/backend/resumes ──► Flow 2 (async)
                  │                                                     │
                  ├── poll GET /resumes/{id}/status every 1.5s ◄────────┘ (until embedding ready)
                  │
                  ├── paste JD ──► /api/backend/jobs ──► Flow 3 ──► poll GET /jobs/{id}/status
                  │
                  ├── Run ──► POST /api/backend/match/{resume_id}/{job_id}?generate_feedback=true
                  │              └──► Flow 4 ──► result: dial + sub-scores + section scores
                  │                     matched skills = resume.parsed_skills ∩ job.parsed_skills
                  │                     missing keywords = match record (scored artefact)
                  │
                  ├── feedback present? render it : stream it
                  │     GET /api/backend/matches/{id}/feedback/stream ──► Flow 5 (SSE via proxy)
                  │     regenerate: POST /matches/{id}/feedback {model} ──► replaces text
                  │
                  ├── bullet improver: POST /ai/rewrite-bullet {bullet, target_job, missing_skills}
                  └── PDF: <a href=/api/backend/matches/{id}/export-pdf> ──► Flow 8
```

## 5. What Calls What: Component Call Tree Matrix

| Module / File | Primary Functions | Called By | Calls Into / Dependencies |
|---|---|---|---|
| **`app/main.py`** | `lifespan()`, exception handlers | Uvicorn ASGI server | `app.api.api_router`, `app.config.settings` |
| **`app/api/auth.py`** | `register()`, `login()` | HTTP Clients | `app.core.security`, `app.database.get_db`, `app.models.user.User` |
| **`app/api/resumes.py`** | `upload_resume()`, `get_resume()`, `get_resume_status()`, `reprocess_resume()`, `recommend_jobs_for_resume()` | HTTP Clients | `app.utils.pdf_parser`, `app.utils.docx_parser`, `app.tasks.resume_tasks`, `app.services.recommendation_service` |
| **`app/api/jobs.py`** | `create_job()`, `list_jobs()`, `get_job()`, `get_job_status()`, `reprocess_job()`, `recommend_jobs_for_resume()` | HTTP Clients | `app.services.keyword_service`, `app.tasks.embedding_tasks`, `app.services.recommendation_service` |
| **`app/api/matches.py`** | `run_match()`, `list_matches()`, `get_match()`, `export_match_pdf()`, `generate_feedback_for_match()`, `stream_match_feedback()` | HTTP Clients | `app.core.rate_limiter`, `app.services.cache_service`, `app.services.matching_service`, `app.services.keyword_service`, `app.services.llm_service`, `app.services.pdf_export_service` |
| **`app/api/analytics.py`** | `resume_version_progress()`, `resume_evaluations_summary()`, `analytics_dashboard()` | HTTP Clients | `app.services.analytics_service`, `app.database.get_db` |
| **`app/api/ai.py`** | `list_models()`, `rewrite_bullet()`, `extract_skills()`, `stream_ai_generation()` | HTTP Clients | `app.services.llm_service`, `app.config.settings` |
| **`app/services/matching_service.py`** | `compute_similarity_score()`, `ensure_embedding()` | `matches.py`, Celery tasks | `app.services.embedding_service`, PostgreSQL pgvector `<=>` |
| **`app/services/recommendation_service.py`** | `get_job_recommendations_for_resume()` | `jobs.py`, `resumes.py` | `app.services.matching_service`, `app.services.keyword_service`, PostgreSQL pgvector `<=>` |
| **`app/services/analytics_service.py`** | `get_resume_progress_for_job()`, `get_resume_evaluations_summary()`, `get_user_analytics_dashboard()` | `analytics.py` | PostgreSQL `match_results`, `resumes`, `job_descriptions` |
| **`app/services/llm_service.py`** | `call_openrouter()`, `stream_openrouter()`, `generate_match_feedback()`, `rewrite_bullet_point()`, `extract_skills_llm()` | `matches.py`, `ai.py`, `llm_tasks.py` | `httpx.AsyncClient`, OpenRouter API |
| **`app/services/cache_service.py`** | `get_cached_match()`, `set_cached_match()`, `invalidate_match_cache()` | `matches.py`, `resumes.py`, `jobs.py` | Redis client (DB 0) |
| **`app/services/embedding_service.py`** | `generate_embedding()`, `compute_cosine_similarity()` | `matching_service.py`, `resume_tasks.py`, `embedding_tasks.py` | `sentence_transformers.SentenceTransformer` (`all-MiniLM-L6-v2`) |
| **`app/services/keyword_service.py`** | `extract_skills()`, `compute_keyword_overlap()`, `find_missing_keywords()`, `compute_section_scores()` | `jobs.py`, `resumes.py`, `matches.py`, `recommendation_service.py` | `app.utils.skills_dictionary` |
| **`app/services/pdf_export_service.py`** | `generate_match_report_pdf()` | `matches.py` | `reportlab.platypus` |
| **`app/tasks/celery_app.py`** | Celery instance | `uvicorn`, Celery worker | Redis (DB 1 broker, DB 2 backend) |
| **`app/tasks/resume_tasks.py`** | `process_resume_task` | `resumes.py` via Celery queue | `app.database.get_sync_db`, `app.services.keyword_service`, `app.services.embedding_service` |
| **`app/tasks/embedding_tasks.py`** | `process_job_task`, `batch_process_embeddings_task` | `jobs.py` via Celery queue | `app.database.get_sync_db`, `app.services.keyword_service`, `app.services.embedding_service` |
| **`frontend/src/proxy.ts`** | Optimistic auth redirects | Next.js runtime (every /app, /login, /signup navigation) | `access_token` cookie presence |
| **`frontend/src/app/api/auth/*`** | `login`, `register`, `logout`, `me` route handlers | Browser (login/signup pages) | FastAPI `/auth/*` via `API_INTERNAL_URL`; sets/clears the httpOnly cookie |
| **`frontend/src/app/api/backend/[...path]/route.ts`** | Generic authenticated proxy | Browser (all app data calls) | FastAPI (any path), attaching the cookie JWT server-side; streams SSE/PDF bodies |
| **`frontend/src/lib/api/client.ts`** | `api.*` typed calls, `ApiError`, `streamMatchFeedback` | React components/hooks | Next.js `/api/*` route handlers only (never FastAPI directly) |
| **`frontend/src/app/app/match/page.tsx`** | Matcher workspace (upload → poll → match → feedback) | Signed-in user | `lib/api/client.ts`, TanStack Query (status polling) |
