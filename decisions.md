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
11. [Phase 11: Frontend (Next.js) & Docker Stack](#11-phase-11-frontend-nextjs--docker-stack)

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

---

## 11. Phase 11: Frontend (Next.js) & Docker Stack

> Phase 11 adds the product's first frontend and its one-command local stack, per
> `ROADMAP.md` (Phases 1 of the roadmap). Entries are appended as each change is
> made, in the order it was made, so this section doubles as the build log of the
> *why* behind the frontend. Sumit's standing instruction for this phase: every
> change records why it was chosen here; `flow.md` is updated at checkpoints.

### 11.1 Web Framework: Next.js 16 (App Router) over Vite + React (the PMS stack)
* **Decision:** The frontend in `frontend/` is **Next.js 16.4.6 (App Router) + React 19 + TypeScript**, scaffolded with `create-next-app` (`--typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`).
* **Rationale:**
  * **This product's growth surface is public pages** — landing page, template gallery, per-template pages, resume examples, a free ATS checker. Those need server/static rendering to be indexed and to load fast. Next.js renders per page (or per component): SSG/SSR/ISR for public pages, client components for the logged-in app. A Vite SPA renders everything after JavaScript loads and needs extra prerendering machinery to reach the same result.
  * **It is still React.** Components, hooks, and Sumit's existing React knowledge transfer directly; the only new model is the App Router / Server Components split. Alternatives that would have discarded that (SvelteKit, Nuxt) or split the app in two (Astro + embedded React app) were rejected for this reason.
  * **FastAPI stays the backend.** Next.js is presentation + rendering only; no business logic moves into Next route handlers (the only server code allowed is the thin auth/BFF proxy, §11.5). This preserves Phases 1–10 untouched.
  * **Version pinning is a security rule, not a preference.** Next 16.4.6 was the current patched line when scaffolded; the October/November 2026 React Server Components advisories make "run the patched release" a hard requirement (§11.9 in a later entry if/when it changes).
  * Scaffold note: Next 16 renamed `middleware.ts` to **`proxy.ts`** and `cookies()` is async — both verified against the framework's own bundled docs (`frontend/node_modules/next/dist/docs/`) before writing auth code, because this version differs from older Next.js conventions.

### 11.2 Local Stack: Docker Compose with Five Services
* **Decision:** Added `docker-compose.yml` at the repo root: `db` (Postgres), `redis`, `api` (FastAPI), `worker` (Celery), `frontend` (Next.js), with healthchecks and named volumes (`pgdata`, `redisdata`). The API service runs `alembic upgrade head` before starting Uvicorn.
* **Rationale:**
  * The original project specification promised "`docker-compose up` should be the whole story", but no Compose file ever existed — local setup meant hand-running four processes plus two databases. This closes roadmap gap G9.
  * **Migrations at API startup** (idempotent) remove the manual `alembic upgrade head` step from first-run setup; the worker starts after the API so tables exist before tasks run.
  * **Secrets stay out of the file:** values interpolate from the shell or a root `.env`; the file carries only safe local defaults, mirroring the backend's existing `.env.example` approach.
  * The worker keeps `--pool=solo` — the Phase 7 decision (§7.3) stands; prefork + PyTorch/Sentence-Transformers is a known crash, and solo is the simplest correct choice for a dev stack.

### 11.3 pgvector Extension: Created by a Postgres Init Script, Not by Alembic
* **Decision:** Added `docker/postgres/init-pgvector.sql` (`CREATE EXTENSION IF NOT EXISTS vector;`), mounted into the db service's `/docker-entrypoint-initdb.d/`.
* **Rationale:**
  * **Found gap while wiring Compose:** the initial Alembic migration creates `VECTOR(384)` columns but *never creates the extension*, so migrations fail against a completely fresh database. On Sumit's machine this was invisible because the extension had been created by hand once.
  * The init script runs exactly once, at first database creation — the right lifecycle for an extension — and keeps the historical migrations untouched (rewriting an applied migration would be worse).

### 11.4 Container Images: Official Slim/Alpine Bases + Next.js Standalone Output
* **Decision:** Backend image is `python:3.12-slim` (one image shared by `api` and `worker`, differing only by command). The Postgres image is `pgvector/pgvector:pg16` and Redis is `redis:7-alpine`. The frontend image is a three-stage `node:24-alpine` build using Next's `output: "standalone"`.
* **Rationale:**
  * `pgvector/pgvector` is the pgvector team's own image (official Postgres + extension), so we never compile pgvector in our Dockerfile.
  * Python 3.12-slim matches the verified local runtime; slim matters because the dependency set (PyTorch via sentence-transformers) is already large.
  * Node 24 satisfies Next 16's Node ≥ 20.9 requirement with headroom; standalone output means the runner stage ships only the server bundle + static assets, not `node_modules` or sources.
  * `NEXT_PUBLIC_API_BASE_URL` is a **build arg**, because `NEXT_PUBLIC_*` values are inlined at build time — passing it as a runtime env var would silently do nothing.

### 11.5 Auth Transport: httpOnly Cookie + a Thin BFF Proxy (Not localStorage)
* **Decision:** Login/register are Next route handlers (`src/app/api/auth/*`). On login, the handler forwards credentials to FastAPI, receives the JWT, and stores it in an **httpOnly, SameSite=Lax cookie** (24 h, matching the backend's token lifetime). One generic proxy handler (`src/app/api/backend/[...path]/route.ts`) forwards every other app API call, attaching `Authorization: Bearer <token>` server-side and streaming response bodies through unbuffered.
* **Rationale:**
  * **The token never touches browser JavaScript.** `localStorage` tokens are readable by any XSS payload; an httpOnly cookie is not. Resume products hold sensitive career data, so this is the default, not an upgrade.
  * **One proxy, every transport:** the same handler carries JSON, multipart resume uploads (forwarded as raw bytes so file bodies are byte-exact), SSE feedback streams, binary PDF downloads, and the backend's standard error envelope — the client therefore has exactly one error shape to handle (`src/lib/api/client.ts`).
  * **FastAPI remains the only authority.** The proxy adds no logic beyond attaching the token; it does not cache, transform, or validate. A 401 from the backend passes through, and `/api/auth/me` clears a dead cookie so stale sessions self-heal.
  * **Route protection is optimistic by design:** `src/proxy.ts` (Next 16's renamed Middleware) only checks the cookie's *presence* to redirect `/app/*` → `/login` and signed-in users away from `/login`. The framework's own auth guide prescribes exactly this split — Proxy for optimistic checks, real validation at the data layer — because Proxy runs on every navigation and must stay fast.
  * **Logout = delete the cookie.** The backend's JWT is stateless (Phase 2, §2.2), so there is nothing server-side to revoke; the trade-off was already accepted there and is unchanged.

### 11.6 Frontend State: TanStack Query for Server State; No Redux
* **Decision:** Installed `@tanstack/react-query` as the only data layer in this phase. **Redux is not used.** Zustand is deferred to the roadmap phase that introduces the resume builder.
* **Rationale:**
  * Everything the Phase 1 UI reads — resumes, jobs, matches, analytics, processing status — is *server state*: it is owned by FastAPI, cached, refetched, and invalidated. TanStack Query is purpose-built for exactly that (including the status polling in §11.8); putting it in Redux would mean hand-writing cache, retry, and refetch logic for no benefit.
  * Sumit's PMS frontend uses Redux, but familiarity is not a reason to use the wrong tool: the state *shapes* differ. PMS holds long-lived client state; this app, in Phase 1, holds almost none.
  * **Zustand is named, not installed:** the builder editor (roadmap Phase 3) will hold nested, high-frequency client state (document tree, undo/redo, unsaved flag) — that is Zustand's job, and adding it now, with no editor to serve, would be speculative.
  * Forms use **React Hook Form + Zod** (`@hookform/resolvers`): Zod schemas mirror the backend's Pydantic contracts (e.g. a job description's 50-character minimum is enforced identically on both sides), so validation errors agree instead of surprising the user after a round trip.

### 11.7 UI System: Tailwind v4 + shadcn/ui (Base UI), Light-First, One Blue Accent
* **Decision:** Styling is Tailwind CSS v4 with shadcn/ui components (neutral base, CSS variables) and Lucide icons. The design language is light-first, clean, content-led, with a single deep-blue accent (`blue-700`) — the same deep blue the backend's PDF report already uses. No component library beyond shadcn's primitives was added.
* **Rationale:**
  * **shadcn is code we own, not a dependency:** components are generated into `src/components/ui/` and edited in place, so the design can diverge freely later (templates phase) without fighting a library's theming system.
  * **One accent, honest states:** a single accent keeps the product from looking like a template; roadmap-phase features (ATS checker, builder, cover letters) are shown on the landing page and in navigation with explicit "Soon / In the roadmap" badges rather than fake working links — the UI never claims a feature exists before its phase ships.
  * **Light-first** matches the reference product class (Enhancv-style tools are light) and the fact that resumes are documents — read on white. Dark mode tokens exist in the generated theme but are not a Phase 1 commitment.
  * **Score display is a custom SVG dial, not a chart library:** one arc with the backend report's own colour tiers (green ≥ 75, amber ≥ 50, red < 50) needs no chart dependency; Recharts enters only when analytics charts are built (roadmap Phase 6).
  * **Learned in this build (recorded so it isn't relearned):** this shadcn generation is built on **Base UI, not Radix** — `Button` has **no `asChild` prop**. Link-styled buttons are therefore `<Link>` elements with `buttonVariants()` classes. Eleven usages were corrected before the first successful production build; `Select`'s change handler also receives `string | null`, which the model picker handles explicitly.

### 11.8 Matcher Data Flow: Poll Status, Stream Feedback, Trust the Cache
* **Decision:** The matcher workspace (`src/app/app/match/page.tsx`) polls `GET /resumes/{id}/status` and `GET /jobs/{id}/status` every 1.5 s via TanStack Query's `refetchInterval` (stopping on `completed`/`failed`), enables **Run match** only when both sides report an embedding, renders `ai_feedback` when the match response already carries it, otherwise **streams** it from `/matches/{id}/feedback/stream` token-by-token, and regenerates through `POST /matches/{id}/feedback` with the user-selected model from `GET /ai/models`. Matched skills are computed client-side as the intersection of the two `parsed_skills` lists.
* **Rationale:**
  * **Polling matches the backend's shape:** uploads return in ~300 ms with processing offloaded to Celery (Phase 7), and a dedicated status endpoint already exists — polling it is the intended consumption pattern; inventing a websocket for this would add a channel the backend doesn't have.
  * **No fake "instant" UX:** repeat matches return from the Redis cache in milliseconds (Phase 6) — the UI shows the result when it arrives, with no artificial delays or staged animations pretending to compute.
  * **Streaming is used only where the backend streams:** first-time feedback generation takes seconds and the SSE endpoint exists for exactly that; regeneration is a single request/response, so it uses the plain POST and replaces the text atomically. The SSE parser in `src/lib/api/client.ts` tolerates events split across chunks and ends on `[DONE]`.
  * **The intersection is honest arithmetic:** "matched skills" is defined by the same skills dictionary on both sides, so intersecting the two parsed lists in the browser reproduces the backend's notion exactly without a new endpoint; the missing list comes from the match record itself, which is the scored artefact.
  * **Client-side file checks mirror server rules** (PDF/DOCX only, 10 MB, JD ≥ 50 chars) so the common failures are instant, while the server remains the authority — its error envelope is what renders when the two disagree.

> **Update (2026-11-13, Sumit's call): Docker usage is deferred.** The Compose stack stays in the repo but is dormant — local development runs natively (Postgres+pgvector and Redis as local services, `uvicorn` + Celery worker, `npm run dev` for the frontend) until most features are complete. Docker returns as the deployment setup in roadmap Phase 8. Nothing in the application code is Docker-specific: both paths are driven by the same environment variables (`DATABASE_URL`, `REDIS_URL`, `API_INTERNAL_URL`), so deferring Docker changes no code.
