# AI Resume Matcher — Detailed Feature Roadmap

**Project:** AI Resume & Job Matcher (`SumitB007/ai-resume-matcher`)
**Date:** 13 November 2026
**Status:** Planning document — no code in this document has been built yet, except where marked ✅ Built
**Reference product (features only, not design/copy):** Enhancv — resume builder, ATS checker, templates, cover letters
**Hero feature (decided):** Check a resume against a job description — match score, what's missing, what to add, AI suggestions

---

## 1. Executive summary and the one decision that shapes everything

The backend matching engine is already built and is the strongest part of this product. What does not exist is everything a normal user touches: there is **no frontend at all**, no resume builder, no templates, no cover letters, and no standalone ATS check.

This roadmap therefore does three things, in order:

1. **Puts a real product in front of the existing engine** — landing page + the JD matcher as the hero tool.
2. **Adds the two scoring products around it** — a standalone ATS checker (no JD needed) and, later, one-click tailoring of a built resume to a JD.
3. **Builds the document products** — structured resume builder, templates, PDF export, cover letters — reusing the same LLM and matching services instead of building a second AI stack.

### Frontend decision: Next.js, not the PMS stack

Sumit explicitly opened this choice: use the better frontend, not necessarily the PMS family (Vite + React + Redux). The better choice for *this* product is different from PMS, for one concrete reason — **this product lives or dies on public, searchable pages; PMS is a logged-in app.**

| Need | Vite + React SPA (PMS stack) | Next.js (App Router) |
|---|---|---|
| Landing page, template gallery, resume examples, free checker pages found on Google | Weak by default — content renders after JavaScript runs; SEO needs extra prerendering work | Strong by default — pages can be static (SSG), server-rendered (SSR), or incrementally regenerated (ISR), per page or even per component |
| Logged-in app: dashboard, matcher, builder editor | Excellent — simple, fast to develop | Excellent — those pages are simply client components; no penalty |
| Routing, layouts, image optimisation, OG images | Add libraries yourself | Built in |
| Familiarity for Sumit | Already known from PMS | Still React + components + hooks — new part is the App Router / Server Components model, not a new language |
| Deployment | Any static host | Vercel (first-class), or any Node host / Docker |

**Recommendation: Next.js 16 (App Router) + TypeScript.** As of this writing the current line is Next.js 16.4.x (16.4.6, 9 Nov 2026) on React 19, requiring Node ≥ 20.9. Pin a patched release (≥ 16.4.5 — the October/November 2026 React Server Components advisories make "latest patched" a hard rule, not a nicety) and treat framework upgrades as routine maintenance.

Alternatives considered and rejected, with reasons:

- **Astro** — superb for content/marketing sites, but the core of this product is a highly interactive editor and app; we'd end up bolting a React app inside Astro islands and maintaining two mental models.
- **SvelteKit / Nuxt** — good frameworks, wrong ecosystem bet here: Sumit already writes React, the component/UI library ecosystem for editors (drag-and-drop, rich inputs, PDF preview) is deepest in React, and hiring/sharing code with PMS stays possible.
- **React Router framework mode / TanStack Start** — credible and closer to Vite, but younger; Next.js has the larger template, UI-kit, and hosting ecosystem for exactly this SaaS shape.
- **Plain Vite SPA** — the right choice if this were only a logged-in tool. It fails the growth plan in §9: template pages, role examples, and the free ATS checker are search landing pages, and an SPA makes each of them harder to rank and slower to first paint.

**What Next.js does *not* replace:** FastAPI stays the backend. We do not move business logic into Next.js API routes. Next.js is presentation + rendering; all matching, scoring, LLM, and document logic stays in the existing Python services. The only Next-side server code allowed is thin: auth token handling helpers, a proxy/rewrites rule to the FastAPI origin, and the print route used for PDF generation (§7.4).

---

## 2. Current state audit — what the repo actually contains

Verified by cloning and reading the full codebase on 12–13 Nov 2026 (single commit `dc47e4d`, ~5,800 lines of Python, `tests/` included). The GitHub connector in this workspace is not connected; the repo was read via a plain public `git clone`.

### 2.1 Stack (backend) ✅ Built

| Layer | Technology | Notes |
|---|---|---|
| API | FastAPI + Uvicorn, Pydantic v2 | Async throughout; global error envelopes; CORS currently `allow_origins=["*"]` (must tighten before launch — §10) |
| Database | PostgreSQL + pgvector | 384-dim vectors, cosine distance via the `<=>` operator |
| Embeddings | `sentence-transformers`, `all-MiniLM-L6-v2` | Local, free, 384-dim; long texts chunked (5,000 chars, 500 overlap) and mean-pooled |
| Background jobs | Celery + Redis | Upload responds ~300 ms with `pending` + `task_id`; worker does parsing/embedding (`--pool=solo`) |
| Cache / limits | Redis | Match cache, 1-hour TTL; rate limit 10 match requests/min/user |
| LLM | OpenRouter via `httpx` | Model-switchable (Mistral 7B, Llama 3.3 70B, Gemini 2.0 Flash, GPT-4o-mini, Claude 3.5 Sonnet); SSE streaming; **intelligent local fallback** when no key / API fails |
| Parsing | `pdfplumber` (PDF), `python-docx` (DOCX) | 10 MB max; <50 extracted chars → 422 |
| PDF | ReportLab | Match *assessment report* only — not a resume document |
| Migrations | Alembic | 2 migrations (initial tables; `task_id` columns) |
| Tests | pytest + pytest-asyncio | Analytics, LLM, PDF export, recommendations, tasks — require live Postgres/Redis fixtures |

### 2.2 Endpoint inventory ✅ Built

- **Auth:** `POST /auth/register`, `POST /auth/login` (JWT, HS256, 24 h), `GET /auth/me`
- **Resumes:** `POST /resumes` (PDF/DOCX upload), `GET /resumes`, `GET /resumes/{id}`, `GET /resumes/{id}/status`, `POST /resumes/{id}/reprocess`, `GET /resumes/{id}/recommendations`
- **Jobs:** `POST /jobs` (raw text, title, company), `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/status`, `POST /jobs/{id}/reprocess`
- **Matching:** `POST /match/{resume_id}/{job_id}` (`?generate_feedback=`, `?model=`), `GET /matches` (filters, sort, pagination), `GET /matches/{id}`, `GET /matches/{id}/export-pdf`, `POST /matches/{id}/feedback`, `GET /matches/{id}/feedback/stream` (SSE)
- **AI:** `GET /ai/models`, `POST /ai/rewrite-bullet`, `POST /ai/extract-skills`, `POST /ai/stream` (SSE)
- **Analytics:** `GET /analytics/dashboard`, `GET /analytics/resume-progress/{job_id}`, `GET /analytics/resumes/{resume_id}/progress`
- **Tasks / health:** `GET /tasks/{task_id}`, `GET /health`, `GET /`

### 2.3 How the core score works ✅ Built

```
overall = 0.60 × semantic similarity (pgvector cosine on 384-dim embeddings)
        + 0.40 × keyword overlap (% of JD skills found in resume)
section scores: skills_match · experience_relevance (category-weighted) · keyword_density
missing keywords: JD skills − resume skills (set difference)
skills source: curated dictionary of 200 tech terms + alias normalisation
               (k8s→kubernetes, postgres→postgresql, js→javascript, …)
AI feedback: strengths · gaps · X-Y-Z bullet rewrites · placement strategy (streamable)
```

### 2.4 Gaps — verified in code, not assumed

| # | Gap | Evidence | Blocks |
|---|---|---|---|
| G1 | **No frontend of any kind** | No `package.json`, JSX/TSX, or HTML in the repo | Everything user-facing |
| G2 | **Resumes are unstructured** — `Resume` stores only `raw_text`, `parsed_skills[]`, embedding, status | `app/models/resume.py` — no name/contact/sections/experience entries | Builder, templates, import-to-builder |
| G3 | **No standalone ATS check** — every score needs a resume_id *and* a job_id | `app/api/matches.py` | Free checker tool, builder's built-in check |
| G4 | **No document model** — no builder documents, templates, cover letters, or versions | Models are only `User`, `Resume`, `JobDescription`, `MatchResult` | Builder, templates, cover letters |
| G5 | **No resume PDF rendering** — ReportLab code renders a match report, not a designed resume | `app/services/pdf_export_service.py` | Template downloads |
| G6 | **Skills dictionary is tech-only (200 terms)** | `app/utils/skills_dictionary.py` | Non-tech roles (sales, marketing, finance, ops…) |
| G7 | **User is email-only** — no name or profile fields | `app/models/user.py` | Builder prefill, personalisation |
| G8 | **Original uploaded file is discarded** — only extracted text is kept | `app/api/resumes.py` | Re-download original, re-parse with a better parser later |
| G9 | **No Docker Compose** — spec promised `docker-compose up` as the whole setup; no Dockerfile/Compose exists | Repo root listing | Easy local dev + deployment |
| G10 | **CORS wide open, no file storage, no email flows** (verify/reset) | `app/main.py` | Public launch |

None of G2–G10 requires replacing existing code. Every gap is an *addition* beside the current services — that is why the Enhancv-style expansion is feasible without a rewrite.

---

## 3. Recommended frontend stack (full)

| Concern | Choice | Why this one |
|---|---|---|
| Framework | **Next.js 16 (App Router), TypeScript strict** | §1 — SSG/SSR/ISR for public pages, client components for the app, React 19 |
| Styling | **Tailwind CSS + shadcn/ui** (Radix primitives) | Fast, ownable components (code lives in the repo, not a locked library), easy custom design system — Enhancv-*like polish* without copying Enhancv |
| Server state | **TanStack Query** | Resumes/jobs/matches are server state: caching, polling task status, retries, invalidation after reprocess — Redux would be hand-rolling all of this |
| Client/editor state | **Zustand** | Builder document state (sections, undo/redo, unsaved flag) is local, nested, and high-frequency — a small store beats Redux boilerplate here. **Redux is deliberately not used**; PMS experience still transfers (same unidirectional idea) |
| Forms | **React Hook Form + Zod** | Zod schemas mirror the backend Pydantic schemas; one validation story per form (auth, JD submit, builder fields, cover letter) |
| Drag & drop | **dnd-kit** | Section reordering and item reordering in the builder; accessible, maintained, React-native |
| Rich text (bullets/summary) | Start with **plain textareas + AI actions**; add **Tiptap** only if inline formatting proves necessary | Bullets are plain text in every ATS — rich formatting in the editor invites ATS-hostile output. Keep v1 honest |
| Charts | **Recharts** (score history, analytics) | Already a familiar React charting choice; score dial itself is a custom SVG arc |
| Streaming | Native **fetch + ReadableStream** for SSE endpoints | Backend already streams (`/feedback/stream`, `/ai/stream`); consume token-by-token for the "AI is writing" effect |
| Icons | **Lucide** | Consistent with modern shadcn setups |
| Testing | **Vitest + Testing Library** (units/components), **Playwright** (critical flows: signup→match, builder→PDF) | Playwright doubles as the PDF engine (§7.4) — one dependency, two jobs |
| Lint/format | ESLint (Next config) + Prettier | Non-negotiable hygiene from day 1 |

**Repo layout decision:** add a `frontend/` folder inside the existing repo (single repo, two apps: FastAPI at root, Next.js in `frontend/`). One repo keeps backend+frontend changes reviewable together and matches how Sumit already works. Revisit a split only if deployment forces it.

**Auth handling (important detail):** the backend issues a JWT (24 h) and expects `Authorization: Bearer …`. For the Next.js app: store the token in an **httpOnly cookie via a thin Next route-handler login proxy** rather than `localStorage`, so public SSR pages and the app share one session story and XSS token theft is harder. FastAPI remains the source of truth for identity (`GET /auth/me`). Token expiry (24 h) means the UI needs a clean re-login redirect, not silent failures.

---

## 4. Product shape — pages and information architecture

### 4.1 Public (no login) — SSG/SSR, these are the growth surface

| Route | Page | Rendering |
|---|---|---|
| `/` | Landing — hero is the JD matcher ("Check your resume against any job description"), then builder/templates/checker sections | Static |
| `/job-match` | The hero tool itself (usable with signup gate at the *run* step — see §5.2) | Static shell + client tool |
| `/resume-checker` | Free standalone ATS checker (upload → score + checks, no JD needed) | Static shell + client tool |
| `/templates` | Template gallery (live previews rendered from sample data) | Static |
| `/templates/[slug]` | One page per template (SEO) | SSG per template |
| `/cover-letter` | Cover letter product page + generator entry | Static |
| `/cover-letter/templates` | Cover letter template gallery | Static |
| `/examples` , `/examples/[role]` | Resume examples per role (later phase, content-driven) | SSG |
| `/login` , `/signup` | Auth | Client |

### 4.2 App (login required) — client-rendered inside Next.js

| Route | Page | Backend it uses |
|---|---|---|
| `/app` | Dashboard — recent resumes, recent matches, best scores, top missing skills | ✅ `/analytics/dashboard` |
| `/app/resumes` | My resumes (uploads) — status, skills count, reprocess, match history per resume | ✅ `/resumes*` |
| `/app/jobs` | Saved job descriptions | ✅ `/jobs*` |
| `/app/match` | Matcher workspace — pick/upload resume + paste JD → results | ✅ `/match/*`, `/ai/*` |
| `/app/matches` | Match history (filter/sort) | ✅ `/matches` |
| `/app/builder` | My documents (builder resumes + cover letters) | 🔨 New (§7) |
| `/app/builder/[id]` | Resume builder editor + live preview | 🔨 New (§7) |
| `/app/cover-letter/[id]` | Cover letter editor + preview | 🔨 New (§8) |
| `/app/analytics` | Progress — score over versions, skills gained | ✅ `/analytics/*` |
| `/app/settings` | Account (name — needs G7 fix — password, delete account/data) | Partly new |

---

## 5. Phase 1 — Frontend foundation + hero JD matcher (the MVP)

**Goal:** a stranger can land on the site, understand it in 10 seconds, sign up, and run the core match end-to-end. Everything else is worthless until this exists.
**Size:** L (largest single phase; it contains all the platform plumbing)

### 5.1 Foundation work

- [ ] Scaffold `frontend/` — Next.js 16 + TS + Tailwind + shadcn/ui, ESLint/Prettier, env config (`NEXT_PUBLIC_API_BASE_URL`)
- [ ] Docker Compose for local dev (fixes G9): Postgres+pgvector, Redis, FastAPI, Celery worker, Next.js — `docker compose up` is the whole story, as the original spec intended
- [ ] Design system v1: colour/typography/spacing tokens, logo/wordmark placeholder, light theme first (dark mode later — do not repeat a two-theme launch burden)
- [ ] API client layer: typed fetch wrapper (auth header/cookie, error-envelope handling matching FastAPI's `{error, type, detail}` shape), TanStack Query provider
- [ ] Auth: signup/login/logout, httpOnly-cookie session via login proxy, protected `/app/*` gate, `/auth/me` hydration, expiry handling
- [ ] Landing page `/` with the matcher as hero (not a generic SaaS hero) + sections for checker/builder/templates marked honestly as they ship

### 5.2 Matcher workspace (`/app/match`, also embedded on `/`)

User flow: **(1)** upload resume (drag-drop PDF/DOCX, 10 MB) *or* pick an existing one → **(2)** paste JD (+ optional title/company) *or* pick a saved one → **(3)** Run match → **(4)** results.

Must handle, because the backend already behaves this way:

- [ ] Upload returns before processing finishes → poll `/resumes/{id}/status` (and `/tasks/{task_id}`) with a real progress state; disable Run until `completed`/embedding ready
- [ ] Run with feedback on → show score immediately, stream AI feedback token-by-token from `/matches/{id}/feedback/stream`
- [ ] Rate limit is real (10/min) → a 429 shows a calm "slow down" state, not an error crash
- [ ] Redis-cached repeat matches return instantly — UI should not fake a loading delay

Results screen (this is the product's centrepiece — spend design effort here):

- [ ] Overall score dial + the two sub-scores (semantic / keyword) shown separately — the honest breakdown is a differentiator, don't hide it in one number
- [ ] Section score bars: skills match, experience relevance, keyword density
- [ ] Matched skills vs **missing keywords** as two clear chip groups, each missing skill with a one-line "where to add this" hint
- [ ] AI feedback rendered as structured sections (strengths / gaps / rewrites / strategy), with per-bullet "rewrite" action using `/ai/rewrite-bullet`
- [ ] Actions: re-run, generate/regenerate feedback (model picker from `/ai/models`), download match report PDF (`/matches/{id}/export-pdf`), save JD for reuse
- [ ] Empty/first-run state that teaches the flow with a sample resume + sample JD (clearly labelled sample data)

**Acceptance criteria:** new user completes signup → upload → JD → streamed feedback → PDF download in one session; a repeat match on the same pair is visibly instant; killing the OpenRouter key still yields fallback feedback, not an error page.

### 5.3 Also in Phase 1 (thin versions)

- [ ] `/app/resumes`, `/app/jobs`, `/app/matches` — simple tables/cards over existing APIs (no new backend)
- [ ] `/app` dashboard — the five numbers from `/analytics/dashboard` + recent matches; keep it simple, the full analytics page is Phase 7

**Explicitly not in Phase 1:** builder, templates, standalone checker, cover letters, payments, dark mode.

---

## 6. Phase 2 — Standalone ATS checker (no JD required)

**Goal:** the free tool that works on *any* resume, like Enhancv's checker (theirs runs 27 checks across 7 groups; ours launches with ~22 checks in 6 groups and grows). This is the top-of-funnel: it needs no JD, no saved job, and gives the builder (§7) its built-in quality panel for free.
**Size:** M · **Backend:** new service + endpoints, reusing `keyword_service` and the parsers

### 6.1 Check catalogue (v1)

| Group | Checks |
|---|---|
| **File & parse** | File type is PDF/DOCX · file ≤ 10 MB · text actually extractable (not a scanned image) · parse didn't garble (character sanity) |
| **Contact & links** | Email present and well-formed · phone present · LinkedIn/URL present · no email in an image/header-only position (heuristic on raw text) |
| **Sections** | Has: summary/objective · experience · education · skills · (bonus: projects/certifications) · section headings use standard names ATSs recognise |
| **Content quality** | Bullets start with action verbs · bullets with numbers/metrics (count and %) · no first-person pronouns overuse · no obvious spelling red flags (dictionary pass) · summary length in range |
| **Skills & keywords** | Skills section extractable · skill count in healthy range · skills appear in experience too, not only in the list |
| **Length & format** | Word count vs experience-level guidance · estimated pages (1–2) · date presence on roles · consistent date formats (heuristic) |

**Scoring:** each check pass/warn/fail with a weight → one ATS score (0–100) *plus* the grouped breakdown. Never show only the number; every failing check carries a "how to fix" line, and where the builder can fix it, a deep link into the builder (§7) once that exists.

### 6.2 Backend design (new)

- `app/services/ats_service.py` — pure functions over `raw_text` + `parsed_skills` (+ file metadata); unit-testable without a DB, same style as `keyword_service`
- `POST /resumes/{id}/ats-check` → runs checks on a stored resume, persists result
- `POST /ats/check-upload` → anonymous-friendly variant for the public tool: parse in memory, run checks, **do not persist** (privacy + abuse story is cleaner); rate-limit by IP in Redis alongside the existing per-user limiter
- New model `AtsCheckResult` (resume_id nullable, user_id nullable, score, `checks` JSON, created_at) + Alembic migration
- JD mode stays separate: when a JD *is* provided, the checker page offers "also check against a job" → hands off to the existing `/match` flow. Two scores, honestly labelled: **ATS readiness** (this phase) vs **job match** (Phase 1)

**Acceptance criteria:** the repo's own `test_resume.pdf` and a deliberately broken resume (image-only, no email, no skills) produce sensible, different scores; every check is covered by a unit test with a fixture text.

---

## 7. Phase 3 — Structured resume builder + templates + resume PDF

**Goal:** users can *create* a resume in the product — not only upload one — edit it with a live preview, pick a template, and download an ATS-safe PDF.
**Size:** XL (the biggest build in this roadmap; split into 3a/3b/3c below)
**This phase fixes G2, G4, G5 and is the prerequisite for Phase 5 tailoring.**

### 7.1 The structured document model (3a — backend first)

One JSON document per resume, validated by Pydantic on the backend and Zod on the frontend (same shape, two languages):

```jsonc
{
  "personal": { "full_name": "", "title": "", "email": "", "phone": "",
                "location": "", "links": [{ "label": "LinkedIn", "url": "" }] },
  "summary": "",
  "experience": [{ "id": "…", "role": "", "company": "", "location": "",
                    "start": "2022-01", "end": null, "current": true,
                    "bullets": ["…"] }],
  "education":  [{ "id": "…", "school": "", "degree": "", "field": "",
                    "start": "", "end": "", "notes": "" }],
  "skills":     { "groups": [{ "label": "Languages", "items": ["Python"] }] },
  "projects":   [{ "id": "…", "name": "", "link": "", "bullets": ["…"] }],
  "certifications": [{ "id": "…", "name": "", "issuer": "", "date": "" }],
  "languages":  [{ "label": "English", "level": "Fluent" }],
  "custom_sections": [{ "id": "…", "title": "", "items": [] }]
}
```

- New table `resume_documents`: `id`, `user_id`, `title`, `template_id`, `theme` JSON (colour/font/spacing choices), `content` JSONB (the document above), `created_at`, `updated_at`; Alembic migration
- CRUD: `POST/GET /documents`, `GET/PUT/DELETE /documents/{id}`, `POST /documents/{id}/duplicate`
- Derived text: on every save, flatten `content` → plain text and store it alongside. **This is the key integration:** a built resume can then be embedded, skill-extracted, ATS-checked (§6 service runs unchanged), and JD-matched (§5 flow) by feeding its flattened text through the *existing* pipeline. Builder resumes and uploaded resumes converge into one system instead of two
- Autosave from the editor (debounced PUT) + explicit saved state in the UI

### 7.2 The editor (3b — frontend)

- Two-pane: form editor left, **live preview right at true A4 proportions**, preview updates on every keystroke (Zustand store → template component)
- Sections: add/remove/reorder (dnd-kit), items: add/remove/reorder, collapse/expand; hide-empty-sections rule in templates
- Per-bullet AI actions (Phase 5 hooks in here; in 3b ship the UI slot with rewrite-bullet, which already exists: `/ai/rewrite-bullet`)
- Built-in ATS panel: run §6 checks against the document's flattened text *live* — this is the Enhancv pattern worth copying functionally: feedback inside the builder, not on another page
- Start paths: blank · pick a template with sample content · **import an uploaded resume** (7.3) · duplicate an existing document

### 7.3 Import an uploaded resume into the builder

- New LLM task: structured extraction — `raw_text` → the §7.1 JSON (new prompt in `llm_service`, JSON-mode parsing with the same markdown-fence cleanup `extract_skills_llm` already does, Pydantic validation, graceful per-section fallback to empty)
- Always lands as a *draft for review*, never silently trusted — parsing will be imperfect and the user must see/correct it
- This is also the long-term fix path for G2 generally: uploads stay as-is; structure is derived on demand

### 7.4 Templates + PDF export (3c)

**Template system:** a template is a React component that takes (`content`, `theme`) and renders print-exact A4 HTML/CSS. One source renders screen preview *and* PDF — no second implementation to drift.

**v1 template set (6, own designs — inspired by categories, never copied):**

1. **Classic** — single column, serif headings, most conservative / ATS-safest
2. **Modern** — single column, sans, strong name/title block
3. **Compact Tech** — single column, dense, skills-forward (our first audience is tech)
4. **Two-Column Sidebar** — skills/education rail + experience main
5. **Minimal** — maximum whitespace, light rules
6. **Graduate** — education/projects-forward for low-experience users

Customisation per document: accent colour, font pairing (from a small ATS-safe set), base size/spacing density, section order (from the editor). That's it for v1 — Enhancv-grade free-form design control is a trap for v1 scope.

**ATS-safe template rules (hard constraints, tested):** real text layer (never rasterised), no text inside images, no tables-for-layout tricks that scramble reading order, standard section headings, contact details in the body (not header/footer), single reading order per column block.

**PDF pipeline — decision:** render the template's print route (`/print/documents/[id]`, a bare Next.js page) with **headless Chromium via Playwright** on the backend/ worker side, `page.pdf()` with print CSS (`@page` A4, margins 0 — the template owns its margins). Preview == PDF by construction, text stays selectable (ATS-safe). Also offer **Download .txt** (flattened text) from day 1 — trivial once §7.1 flattening exists — and park DOCX export as a later add-on.
Spike first (half the risk in this phase lives here): prove one template through the full loop — editor → print route → Playwright PDF → parse the PDF back with `pdfplumber` and assert the extracted text order is correct. If Chromium hosting proves painful, the fallback is WeasyPrint (HTML/CSS → PDF) with the same templates constrained to its CSS subset — decide from the spike, not in advance.

**Acceptance criteria (whole phase):** a user builds a resume from blank, reorders sections, switches template + colour, sees the ATS panel improve as they fix checks, downloads a PDF whose text extracts in correct order with `pdfplumber`, then runs that same document through the Phase 1 matcher against a JD without re-uploading anything.

---

## 8. Phase 4 — Cover letters (templates + generator)

**Goal:** the second document product, deliberately reusing Phase 3's machinery so this is a small phase, not a second builder project.
**Size:** M · **Depends on:** Phase 3 (document model pattern, template engine, PDF pipeline)

- Model `cover_letters`: `id`, `user_id`, `title`, `template_id`, `theme` JSON, `content` JSONB — `{ sender (from profile/resume), recipient {name, company, role}, date, greeting, paragraphs[], closing, signature_name }`, plus optional `resume_document_id` / `job_id` links
- Editor: same two-pane pattern, paragraph-level editing; templates = the same 6 visual identities as resumes, adapted to a letter layout (matching resume + letter is the Enhancv behaviour users actually value)
- **Generator:** `POST /ai/cover-letter` — inputs: a resume (uploaded or built) + a JD (saved or pasted) + tone (professional / enthusiastic / concise) → structured draft paragraphs via a new `llm_service` prompt, streamed (SSE pattern already exists). Output lands in the editor as an editable draft — never a dead-end text box
- Endpoints mirror documents: CRUD + duplicate + PDF via the same print-route/Playwright pipeline (`/print/cover-letters/[id]`)
- Sample/template content: 3–4 written sample letters (tech roles first) for the gallery pages; gallery is SSG like `/templates`

**Acceptance criteria:** from a match result, one click creates a cover-letter draft for that resume+JD pair, editable, in the matching template, downloadable as PDF.

---

## 9. Phase 5 — AI resume generator + one-click tailoring

**Goal:** the AI features that make the builder feel magical — and the tailoring loop that ties the whole product together around the hero matcher.
**Size:** M–L · **Depends on:** Phase 3 (builder), Phase 1 (matcher); reuses `llm_service` throughout

### 9.1 Generator features (new prompts/endpoints on the existing LLM service)

| Feature | Endpoint | Notes |
|---|---|---|
| Summary generator | `POST /ai/generate-summary` | Inputs: title, years, top skills, target role → 3 variants (length/tone), pick-to-insert |
| Bullet generator | `POST /ai/generate-bullets` | Inputs: role + company + what-you-did (rough notes) → X-Y-Z bullets; the user supplies facts, AI supplies form — prompts must forbid inventing employers/metrics the user didn't state |
| Full draft from job title | `POST /ai/generate-resume-draft` | Title + experience level + skills → a complete §7.1 document skeleton to edit; the "start from nothing" path for `/app/builder` |
| Skills suggester | `POST /ai/suggest-skills` | Role/JD → skill groups for the document, intersected with the dictionary + LLM extraction |
| Cover letter | `POST /ai/cover-letter` | Built in Phase 4 |

All of them: model picker parity with existing `/ai/models`, local-fallback behaviour parity (degraded but functional without a key), and streaming where output is long.

### 9.2 One-click tailoring (the differentiator — design it carefully)

Flow: in the builder, **Tailor to a job** → paste/select JD → backend runs the document's flattened text through the existing matcher → UI shows, side-by-side per suggestion:

- Missing keywords → suggested skills-section additions and bullet insertions
- Weak bullets → rewrites (existing `/ai/rewrite-bullet` with the JD as context)
- Summary → a tailored variant

**Every change is accept/reject individually. Nothing auto-overwrites the user's document.** Tailoring saves as a *duplicate document* ("Resume — tailored for {Company}") by default, keeping the master resume intact — this version-per-job model is also exactly what the existing analytics (score progress per job) was built to visualise.
Live match score for the open document against the selected JD, updating as suggestions are accepted — the builder, checker, and matcher become one loop:

```
build → ATS-check (§6) → tailor to JD (§9.2) → match score (§5) → fix → export PDF (§7.4)
```

**Guardrail:** AI must not fabricate experience. Prompts state it, UI copy states it, and rewrites are framed as rephrasing the user's own facts + surfacing skills the user confirms they have (a missing keyword the user doesn't actually know must be skippable without penalty language).

---

## 10. Phase 6 — Dashboard, analytics, recommendations (frontend for what already exists)

**Size:** S–M · **Backend:** ✅ already built — this phase is almost pure frontend

- `/app` dashboard v2: totals, average/best score, **top missing skills across all matches**, top candidate skills, recent matches (`/analytics/dashboard`)
- `/app/analytics`: per-job progress — initial vs latest score, improvement, skills gained timeline (`/analytics/resume-progress/{job_id}`); per-resume summary across jobs (`/analytics/resumes/{id}/progress`)
- Recommendations panel on a resume: jobs ranked by pgvector similarity with matching/missing skills (`/resumes/{id}/recommendations`) — present honestly as "jobs you've saved that fit this resume", since the catalogue is the user's own jobs, not a job board
- Match history upgrades: compare two matches for the same job (version story), re-export reports

## 11. Phase 7 — Growth surface (SEO/content) — after the product works

**Size:** ongoing · **Why last:** content pages for a product that doesn't exist yet help nobody; with Phases 1–4 live, each page below links into a working tool.

- Per-role example pages (`/examples/[role]`) generated from real template + sample documents (SSG), tech roles first (matches G6 reality), expanding with the skills dictionary
- Checker and matcher as free, indexable tools with their own landing copy (already routed in §4.1)
- Template pages enriched per template (who it's for, ATS notes) — unique content, not gallery clones
- Structured data (WebApplication/FAQ), sitemap, OG images per template/example, Core Web Vitals budget on public pages (they're static — keep them fast)
- Blog/guides: deliberately out of scope until the above exists; if started, it lives in the same Next.js app as MDX

## 12. Phase 8 — Hardening & launch readiness

- [ ] **Security:** CORS tightened from `*` to the real frontend origin (G10); JWT secret/expiry review; upload scanning expectations set (type+size already validated); rate limits extended to auth + anonymous checker; Next.js pinned to patched releases (§1)
- [ ] **Privacy (resumes are PII):** privacy policy + data-deletion (account delete cascades documents/matches), anonymous checker truly non-persistent (§6.2), no resume text in logs/analytics, OpenRouter data-handling noted in the policy
- [ ] **Accounts:** name field (G7), password reset + email verification (needs a mail provider — the current backend has no email sending at all; decide provider in this phase)
- [ ] **Cost controls:** LLM spend is the variable cost — per-user daily AI caps (Redis, existing limiter pattern), default to a free/cheap model, cache generations where inputs are identical
- [ ] **Deployment:** Vercel (Next.js) + FastAPI/Celery/Postgres/Redis on a container host (Railway/Render/Fly — decide by Postgres+pgvector support and Redis pricing at the time); Playwright/Chromium runs in the API/worker image; managed Postgres backups on
- [ ] **Observability:** structured logs, error tracking (e.g. Sentry both sides), uptime + the existing `/health`
- [ ] **Payments/subscriptions: explicitly parked.** Not in any phase above. If ever added, it's a Phase 9 decision with its own document — the product proves value free first

## 13. Backend additions — consolidated list

| Addition | Phase | Type |
|---|---|---|
| Docker Compose (Postgres+pgvector, Redis, API, worker, frontend) | 1 | Infra (G9) |
| `ats_service` + `POST /resumes/{id}/ats-check`, `POST /ats/check-upload`, `AtsCheckResult` model | 2 | Service + API + migration (G3) |
| `resume_documents` model + CRUD/duplicate + text flattening on save | 3a | Model + API + migration (G2/G4) |
| Structured import (LLM extraction → document JSON) | 3b | LLM prompt + API |
| PDF print pipeline (Playwright) + `.txt` export | 3c | Worker/API (G5) |
| `cover_letters` model + CRUD + PDF | 4 | Model + API + migration |
| `POST /ai/cover-letter` | 4 | LLM prompt |
| `POST /ai/generate-summary`, `/generate-bullets`, `/generate-resume-draft`, `/suggest-skills` | 5 | LLM prompts |
| Skills dictionary expansion beyond tech (per-role packs) | 5–7, ongoing | Data (G6) |
| User `name` field; email flows (verify/reset) | 8 | Model + migration (G7) |
| CORS lockdown, anonymous rate limiting, AI usage caps | 2/8 | Config + limiter |

## 14. Risks and honest caveats

1. **Import parsing quality (7.3)** — LLM structured extraction will misplace sections on messy resumes. Mitigated by draft-review UX; do not market it as one-click-perfect.
2. **PDF fidelity** — the §7.4 spike exists because Chromium print CSS is the one genuinely uncertain technical piece. Fallback (WeasyPrint) is named in advance so a bad spike costs days, not the phase.
3. **Skills coverage (G6)** — a 200-term tech dictionary makes v1 a *tech-first* product whether we say so or not. Own that positioning in copy until per-role packs land; fake-generality would show instantly in bad scores for non-tech users.
4. **LLM cost/abuse on free tools** — the anonymous checker runs parsers/embeddings, not LLMs, by design (§6.2); AI generation stays behind login with caps (§12).
5. **Enhancv is a reference, not a template** — features, flows, and check categories are fair reference; their template designs, copy, and branding must not be reproduced. All templates here are original designs (§7.4).
6. **Backend not yet live-verified in this workspace** — this roadmap is grounded in a full code read; the FastAPI suite needs Postgres+pgvector/Redis to run, which Phase 1's Compose file fixes permanently. First build task in Phase 1 is standing the stack up and running the existing pytest suite green.

## 15. Decisions for Sumit (with the recommendation baked in)

1. **Frontend: Next.js 16 + TypeScript** — recommended in §1/§3. *(Your "use the better one" note is taken as a yes unless you say otherwise.)*
2. **Scope v1: tech-first roles** — recommended (matches the skills dictionary); all-profession support grows in Phases 5–7.
3. **Template count v1: 6** — recommended over matching Enhancv's catalogue size; quality + PDF correctness over quantity.
4. **Product name/domain** — open. The repo name ("AI Resume Matcher") describes the hero feature well; the builder expansion may want a brand name later. Not blocking Phase 1.
5. **Hosting targets** — deferred to Phase 8 on purpose; only Compose (local) is decided now.

## 16. Immediate next step (when you say go)

Phase 1, first slice only: Compose stack up → existing backend tests green → `frontend/` scaffold with the stack in §3 → auth working against the real API → matcher workspace wired to the existing endpoints. Landing-page polish and the rest of Phase 1 follow in the same phase, but that first slice proves the entire architecture end-to-end before any design effort is spent.

---

*Sources for the frontend decision: Next.js current release line 16.4.x / React 19 (npm, Nov 2026); App Router rendering model (SSG/SSR/ISR + Server Components) per Next.js documentation summaries checked 13 Nov 2026. Repo facts (§2) are from a direct read of `SumitB007/ai-resume-matcher` at commit `dc47e4d`. Enhancv feature references are from enhancv.com, checked 13 Nov 2026.*
