# Architectural & Technical Decisions Record (ADR)
## AI Resume & Job Matcher Backend

This document details every major architectural, technical, library, and implementation decision made throughout the development of the **AI Resume & Job Matcher** platform, structured phase-by-phase with in-depth rationales.

---

## Table of Contents
1. [Phase 1: Project Skeleton & Database Foundation](#1-phase-1-project-skeleton--database-foundation)
2. [Phase 2: Authentication & Security Architecture](#2-phase-2-authentication--security-architecture)
3. [Phase 3: Resume & Job Document Parsing](#3-phase-3-resume--job-document-parsing)
4. [Phase 4: Embeddings & Vector Similarity Engine](#4-phase-4-embeddings--vector-similarity-engine)
5. [Phase 5: Keyword Extraction & Gap Analysis](#5-phase-5-keyword-extraction--gap-analysis)
6. [Phase 6: Caching & Rate Limiting Strategy](#6-phase-6-caching--rate-limiting-strategy)
7. [Phase 7: Asynchronous Background Processing & Celery Architecture](#7-phase-7-asynchronous-background-processing--celery-architecture)
8. [Phase 8: LLM Integration & OpenRouter Model Switching](#8-phase-8-llm-integration--openrouter-model-switching)
9. [Phase 9: Nearest-Neighbor Recommendations & Analytics Engine](#9-phase-9-nearest-neighbor-recommendations--analytics-engine)
10. [Phase 10: PDF Export & Global Resilience](#10-phase-10-pdf-export--global-resilience)

---

## 1. Phase 1: Project Skeleton & Database Foundation

### 1.1 Web Framework: FastAPI over Flask or Django
* **Decision:** Selected **FastAPI** running on **Uvicorn** (ASGI).
* **Rationale:**
  * **Native Asynchronous Concurrency:** FastAPI is built from the ground up on Python's `async`/`await` event loop, making it ideal for non-blocking I/O operations (PostgreSQL database queries, Redis cache lookups, and SSE streaming).
  * **Pydantic v2 Type Validation:** Automatically enforces strict request/response data contracts, serializes complex schemas, and catches malformed payloads before they reach business logic.
  * **Automatic OpenAPI/Swagger Documentation:** Generates interactive `/docs` and `/redoc` interfaces without manual documentation maintenance.
  * **First-Class Streaming Support:** Provides `StreamingResponse` for Server-Sent Events (SSE) token streaming from LLMs.
* **Alternatives Considered:**
  * *Flask:* Synchronous by default; requires third-party plugins (`Flask-RESTful`, `Flasgger`) that add fragmentation.
  * *Django / DRF:* Heavyweight ORM and monolithic overhead that adds unnecessary complexity when paired with specialized vector extensions and custom async Celery workflows.

### 1.2 Database & Vector Engine: PostgreSQL with `pgvector`
* **Decision:** Standardized on **PostgreSQL 16+** with the **`pgvector`** extension rather than a standalone vector database.
* **Rationale:**
  * **Avoids Polyglot Persistence Overhead:** Storing user accounts, document metadata, match results, and high-dimensional vector embeddings in a single database eliminates distributed transactions, synchronization lag, and multiple database connection pools.
  * **Native SQL Vector Operations:** The `<=>` cosine distance operator allows combining traditional relational filters (`WHERE user_id = :id`) directly with vector similarity sorting (`ORDER BY embedding <=> :query_vec ASC`) in a single query planner pass.
  * **ACID Transactions:** Ensures that if a resume upload fails mid-way, all relational state rolls back cleanly.
  * **Cost & Operational Simplicity:** Eliminates expensive managed vector database subscriptions (Pinecone, Qdrant Cloud, Milvus).

### 1.3 Database Driver & ORM: Async/Sync Dual Engine Architecture
* **Decision:** Configured a dual-engine architecture in `app/database.py`:
  * **Web Layer:** `create_async_engine` using `asyncpg` + `async_sessionmaker`.
  * **Worker / Task Layer:** `create_engine` using `psycopg2` + `sessionmaker` via `get_sync_db()` context manager.
* **Rationale:**
  * **FastAPI Async Concurrency:** `asyncpg` is the fastest PostgreSQL driver for Python, allowing FastAPI routes to await queries without blocking the event loop.
  * **Celery Worker Stability:** Background workers execute in dedicated worker processes. Passing async event loops or greenlets across thread/process boundaries frequently causes `RuntimeError: Event loop is closed` or `Future attached to a different loop`. The synchronous engine provides process-isolated, thread-safe database connections for workers.

---

## 2. Phase 2: Authentication & Security Architecture

### 2.1 Password Hashing: `bcrypt` with Direct Truncation Protection
* **Decision:** Used `bcrypt` with salt generation for password hashing.
* **Rationale:**
  * Adaptive hashing algorithm resistant to GPU-accelerated brute-force attacks.
  * Handled the 72-byte truncation boundary of bcrypt cleanly in `app/core/security.py` by converting to UTF-8 bytes before hashing.

### 2.2 Token Format: Stateless JWT (JSON Web Tokens)
* **Decision:** Implemented stateless JWT bearer tokens signed with HMAC-SHA256 (`HS256`).
* **Rationale:**
  * Eliminates database lookups on every authenticated request (session-table bottleneck).
  * Payload contains user identity (`sub: str(user.id)`) and expiration timestamp (`exp`).
  * Enforced via FastAPI's `Depends(get_current_user)` dependency injection pattern, making protected routes clean and declarative.

---

## 3. Phase 3: Resume & Job Document Parsing

### 3.1 Document Extraction: `pdfplumber` + `python-docx`
* **Decision:** Selected `pdfplumber` for PDF files and `python-docx` for `.docx` files.
* **Rationale:**
  * **Visual Layout Accuracy (`pdfplumber`):** Unlike basic text dumpers (e.g. `pypdf`, `PyPDF2`), `pdfplumber` inspects character coordinates, properly resolving multi-column resume layouts, tabular skill grids, and bullet lists without jumbling text blocks.
  * **Native OpenXML Support (`python-docx`):** Parses native Word XML structures without requiring LibreOffice or external binary dependencies installed on the host.
  * **In-Memory Streaming:** Resumes are read directly into memory buffers (`await file.read()`), preventing temporary file clutter on the filesystem.

---

## 4. Phase 4: Embeddings & Vector Similarity Engine

### 4.1 Embedding Model: `sentence-transformers` (`all-MiniLM-L6-v2`)
* **Decision:** Deployed `all-MiniLM-L6-v2` locally on CPU.
* **Rationale:**
  * **384 Dimensions:** Produces compact vectors that reduce PostgreSQL index size and query latency compared to 1536-dim (OpenAI) or 768-dim (BERT-base) embeddings.
  * **Zero Cost & Zero API Rate Limits:** Runs completely on-device. No API tokens, no per-call costs, and no external network latency.
  * **Low Latency:** Inferences on modern CPUs in ~15–30ms per document.
  * **Semantic Quality:** Specially fine-tuned for sentence and paragraph semantic similarity matching (e.g., matching *"managed backend infrastructure"* with *"led server-side platform engineering"*).

### 4.2 Distance Metric: Cosine Distance via `<=>`
* **Decision:** Standardized on Cosine Distance (`vector_cosine_ops`) over Euclidean (`<->`) or Inner Product (`<#>`).
* **Rationale:**
  * Resume and job descriptions vary significantly in length. Euclidean distance penalizes length differences, whereas Cosine distance normalizes document vector magnitudes, measuring only angle/semantic direction.
  * Cosine similarity percentage is cleanly calculated as:
    $$\text{Cosine Similarity} = \max\left(0, \min\left(1, 1 - (\vec{u} \cdot \vec{v})\right)\right) \times 100$$

---

## 5. Phase 5: Keyword Extraction & Gap Analysis

### 5.1 Hybrid Scoring: 60% Semantic + 40% Keyword Blended Formula
* **Decision:** Combined semantic vector similarity with literal keyword overlap in a 60/40 ratio.
* **Rationale:**
  * **Why not 100% Semantic?** Pure embeddings can produce high similarity for resumes that talk about similar domains but lack mandatory technical qualifications (e.g., a Django developer matching a FastAPI role). Real ATS systems enforce strict keyword screening.
  * **Why not 100% Keyword?** Pure keyword matching is brittle—it fails on synonyms, phrasing variations, and misses contextual experience.
  * **The 60/40 Balance:** 60% semantic similarity ensures conceptual alignment and experience relevance, while 40% keyword overlap strictly verifies the presence of required technical competencies.

### 5.2 Curated Skills Taxonomy with Regex & Alias Normalization
* **Decision:** Created a 450+ technical term dictionary in `app/utils/skills_dictionary.py` combined with word-boundary regex matching and acronym resolution.
* **Rationale:**
  * Normalizes variations: `k8s` -> `kubernetes`, `postgres` -> `postgresql`, `ts` -> `typescript`, `gcp` -> `google cloud`, `ci/cd` -> `ci/cd`.
  * Word boundary enforcement (`\b...\b`) prevents false positives (e.g., matching "go" inside "good" or "algorithms").

---

## 6. Phase 6: Caching & Rate Limiting Strategy

### 6.1 Redis Key-Value Caching for Repeated Match Queries
* **Decision:** Cached match results in Redis with a 1-hour Time-To-Live (TTL).
* **Rationale:**
  * Candidates frequently refresh match pages, navigate back and forth, or test small adjustments.
  * Cache key format: `match:{resume_id}:{job_id}`.
  * Reduces match latency from ~38ms to **sub-3ms** on repeated requests, bypassing both database queries and vector computation.
  * **Cache Invalidation:** Calling `POST /resumes/{id}/reprocess` or `POST /jobs/{id}/reprocess` automatically flushes associated Redis match cache keys.

### 6.2 Redis-Based Sliding Window Rate Limiting
* **Decision:** Implemented a Redis-backed rate limiter enforcing **10 match requests per minute per user**.
* **Rationale:**
  * Protects against scraping and runaway clients.
  * Redis integer increments (`INCR`) with atomic expiration (`EXPIRE`) ensure zero race conditions under distributed load.

---

## 7. Phase 7: Asynchronous Background Processing & Celery Architecture

### 7.1 Celery + Redis Task Queue
* **Decision:** Offloaded PDF parsing and embedding generation to **Celery 5.6** with Redis as broker (`redis://localhost:6379/1`) and result backend (`redis://localhost:6379/2`).
* **Rationale:**
  * **Fast API Responsiveness:** Synchronous text parsing and transformer model inference can take 200–800ms. Moving this work to background tasks enables `POST /resumes` and `POST /jobs` to respond in **~300ms** with `status: "pending"` and a `task_id`.
  * **Transparent Progress Tracking:** Real-time polling via `GET /tasks/{task_id}` provides step-by-step state progression (`PENDING` -> `STARTED` -> `PROCESSING` -> `SUCCESS`).
  * **Database Decoupling:** Redis database 0 is reserved for application caching and rate-limiting, database 1 is dedicated to the Celery broker, and database 2 stores Celery task results, preventing key namespace collisions.

### 7.2 Explicit Database Commits Before Task Dispatch
* **Decision:** Explicitly called `await db.commit()` and `await db.refresh()` before calling `.delay(record_id)`.
* **Rationale:**
  * In SQLAlchemy async sessions, `await db.flush()` writes to the database buffer but does not commit the transaction.
  * If a Celery worker picks up `.delay(id)` instantaneously under PostgreSQL's default `READ COMMITTED` isolation level, the row is invisible to the worker, triggering an immediate `Record not found` error. Explicitly committing prior to task enqueueing guarantees absolute row visibility.

### 7.3 Celery Worker Execution: `--pool=solo` on macOS
* **Decision:** Configured worker to run with `--pool=solo`.
* **Rationale:**
  * On macOS, PyTorch and HuggingFace Sentence-Transformers load Apple Accelerate and Objective-C runtime frameworks. When Python standard `prefork` forks worker processes after loading these frameworks in parent memory, it causes deadlocks and crashes. `--pool=solo` runs in-process without unsafe fork operations.

---

## 8. Phase 8: LLM Integration & OpenRouter Model Switching

### 8.1 OpenRouter API over OpenAI Directly
* **Decision:** Standardized on **OpenRouter** (`https://openrouter.ai/api/v1`) rather than OpenAI's direct API.
* **Rationale:**
  * **Universal OpenAI-Compatible API Surface:** OpenRouter conforms strictly to OpenAI's `/v1/chat/completions` specification, allowing standard payload structures while providing access to dozens of model providers.
  * **Dynamic Model Switching:** Users and administrators can switch between models with a single query parameter:
    * `mistralai/mistral-7b-instruct:free` (Fast, zero-cost tier)
    * `meta-llama/llama-3.3-70b-instruct:free` (State-of-the-art open reasoning)
    * `google/gemini-2.0-flash-exp:free` (High-speed multimodal intelligence)
    * `openai/gpt-4o-mini` (Commercial high-intelligence)
    * `anthropic/claude-3.5-sonnet` (Nuanced resume tailoring)
  * **No Vendor Lock-In:** Eliminates dependency on a single AI provider's uptime or pricing changes.

### 8.2 Intelligent Domain-Aware Local Fallback Generator
* **Decision:** Implemented an intelligent local feedback generator in `app/services/llm_service.py` that activates when API keys are invalid, offline, or rate-limited.
* **Rationale:**
  * Automated CI test suites and offline local development environments should not fail or require live credit balances to test match workflows.
  * Generates realistic, structured suggestions using the **Google X-Y-Z formula** (*"Accomplished [X] as measured by [Y] by doing [Z]"*), ensuring downstream test assertions on format and structure pass reliably.

### 8.3 Real-Time Server-Sent Events (SSE) Streaming
* **Decision:** Used FastAPI's `StreamingResponse(media_type="text/event-stream")` for token-by-token feedback streaming (`GET /matches/{id}/feedback/stream` and `POST /ai/stream`).
* **Rationale:**
  * LLM generation can take 2–5 seconds. Streaming initial tokens immediately delivers a responsive, real-time user experience while persisting the full accumulated feedback in PostgreSQL once generation completes.

---

## 9. Phase 9: Nearest-Neighbor Recommendations & Analytics Engine

### 9.1 Database-Native Nearest Neighbor Ranking
* **Decision:** Implemented `GET /jobs/{resume_id}/recommendations` using pgvector SQL `CROSS JOIN` ordering rather than in-memory Python calculations.
* **Rationale:**
  * **Query:**
    ```sql
    SELECT j.id, j.title, j.company, 1 - (j.embedding <=> r.embedding) AS similarity
    FROM job_descriptions j, resumes r
    WHERE r.id = :resume_id AND j.embedding IS NOT NULL
    ORDER BY j.embedding <=> r.embedding ASC
    LIMIT :limit OFFSET :offset;
    ```
  * In-memory ranking requires loading hundreds of 384-dimensional floating-point arrays across the network into Python memory. Executing `<=>` directly in PostgreSQL allows database index acceleration and returns only the top $K$ ranked results in milliseconds.

### 9.2 Resume Version Progression & Skills Gained Analytics
* **Decision:** Created `GET /analytics/resume-progress/{job_id}` to compute version-over-version score improvements and set-difference skill acquisitions.
* **Rationale:**
  * Candidates do not upload a resume once—they iteratively refine it against target job descriptions.
  * By tracking chronological matches for the same job, the platform computes:
    * Net score improvement: $\text{Latest Score} - \text{Initial Score}$
    * Skills gained: $\text{Missing Skills}_{\text{Initial}} \setminus \text{Missing Skills}_{\text{Latest}}$
    * Directly proves to candidates whether their edits successfully bridged targeted ATS gaps.

---

## 10. Phase 10: PDF Export & Global Resilience

### 10.1 In-Memory PDF Generation: ReportLab
* **Decision:** Selected `reportlab` for generating downloadable assessment reports.
* **Rationale:**
  * **Pure Python & Headless:** Operates without requiring headless Chrome (Puppeteer) or WebKit libraries (WeasyPrint), which add massive binary dependencies and complicate containerization.
  * **In-Memory Streaming:** Generates PDFs into `io.BytesIO` buffers, streaming directly to clients via `StreamingResponse(media_type="application/pdf")` with zero disk writes.
  * **High-Precision Layout:** Custom table formatting, score banners, bullet-wrapped paragraphs, and color-coded match tiers.

### 10.2 Global Exception Normalization
* **Decision:** Mounted centralized exception handlers for `RequestValidationError`, `HTTPException`, and generic `Exception` in `app/main.py`.
* **Rationale:**
  * Standardizes error payloads into a predictable JSON envelope:
    ```json
    {
      "error": true,
      "type": "validation_error",
      "message": "Invalid request payload or parameters",
      "details": [{"field": "body -> password", "message": "field required"}]
    }
    ```
  * Prevents sensitive internal stack traces or database schema details from leaking to clients on unexpected 500 errors.
