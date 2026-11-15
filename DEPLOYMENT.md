# Deployment — AI Resume Matcher

How to take the stack live, and the decisions that are still the owner's.

## The stack

| Piece | Runs as | Notes |
|---|---|---|
| Next.js frontend | Vercel **or** the `frontend` compose service | Needs `API_INTERNAL_URL` (server-side reach to the API) and `NEXT_PUBLIC_SITE_URL` (build-time) |
| FastAPI API | container (`Dockerfile`) | Runs `alembic upgrade head` at startup under Compose |
| Celery worker | same image, worker command | `--pool=solo` (established Phase 7/§7.3) |
| Postgres 16 + pgvector | managed Postgres with the `vector` extension, or the compose `db` service | The `ats_matcher` DB needs `CREATE EXTENSION vector` before migrations (compose does it via `docker/postgres/init-pgvector.sql`) |
| Redis | managed or compose service | Three logical DBs: cache (0), Celery broker (1), results (2); rate limits live in 0 |

Local / single-host launch is one command: `docker compose up --build`
(ports: frontend 3000, API 8000, Postgres 5432, Redis 6379).

## Environment checklist (production)

Backend:
- `SECRET_KEY` — a real random value (the app logs a warning at startup while the default is in use; tokens signed with the default are forgeable)
- `DATABASE_URL` / `DATABASE_URL_SYNC` — managed Postgres URLs (`postgresql+asyncpg://…`, `postgresql+psycopg2://…` or `+psycopg://…`)
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `CORS_ORIGINS` — the exact frontend origin, e.g. `https://your-domain.com` (comma-separate several). Never `*`.
- `OPENROUTER_API_KEY` — optional; without it, AI features use the honest local fallbacks
- `AI_DAILY_CAP` — per-user daily AI generation cap (default 100)
- `NEXT_PUBLIC_SITE_URL` (frontend build) — the public domain, drives canonical URLs, sitemap, robots

## Decisions still open (owner)

1. **Hosting for the API/worker/Postgres/Redis** — any container host works with the compose file as-is; if splitting services, pick a Postgres that offers the **pgvector extension** (that is the hard constraint) and turn on its automated backups — resumes are PII.
2. **Email provider** — password reset and email verification are *not* built: the backend has no mail sending at all. Pick a provider (any SMTP/transactional service) and that becomes a small follow-up phase: token tables + two flows. Until then, account recovery is manual.
3. **Error tracking** — `/health` exists and logs are structured by the platform; add Sentry (both sides) when there's a DSN to point at.

## Go-live checklist

- [ ] `docker compose up --build` (or the split-host equivalent) comes up healthy: `/health` on the API, frontend loads, signup → upload → match works end-to-end
- [ ] `CORS_ORIGINS` set to the real origin; a request from any other origin gets no `Access-Control-Allow-Origin`
- [ ] `SECRET_KEY` is not the default (no warning in API logs)
- [ ] Postgres backups enabled; one restore tested
- [ ] `NEXT_PUBLIC_SITE_URL` is the real domain; `/sitemap.xml` and `/robots.txt` show it
- [ ] `/privacy` reviewed — it describes the system as built; keep it in sync when behaviour changes
- [ ] Rate limits sanity-checked: anonymous checker 429s after 5/min from one IP

## Rollback

Every phase ships as one PR into `main`; reverting the PR reverts the phase.
Migrations are the only forward-only piece — each ships a `downgrade()`; run
`alembic downgrade -1` before reverting a PR that added one.
