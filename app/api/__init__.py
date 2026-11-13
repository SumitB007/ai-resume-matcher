"""API Routes Package."""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.resumes import router as resumes_router
from app.api.jobs import router as jobs_router
from app.api.matches import router as matches_router
from app.api.tasks import router as tasks_router
from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.ats import router as ats_router

# ── Root API Router ──
api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(resumes_router, prefix="/resumes", tags=["Resumes"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(matches_router, tags=["Matches"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(ai_router, prefix="/ai", tags=["AI & LLM"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
# ATS routes carry their own full paths (/resumes/{id}/ats-check, /ats/check-upload)
api_router.include_router(ats_router, tags=["ATS Checker"])


