"""AI Resume & Job Matcher — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # ── Startup ──
    print(f"🚀 Starting {settings.app_name}...")
    print(f"📊 Debug mode: {settings.debug}")
    print(f"🗄️  Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'configured'}")

    yield

    # ── Shutdown ──
    print(f"👋 Shutting down {settings.app_name}...")


app = FastAPI(
    title=settings.app_name,
    description=(
        "A backend service that takes a resume and a job description, "
        "computes a match score via semantic similarity and keyword analysis, "
        "identifies skill gaps, and generates AI-powered improvement suggestions."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routes ──
app.include_router(api_router)


# ── Global Exception Handlers ──
from fastapi import Request, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

app_logger = logging.getLogger(__name__)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic request validation errors into a clean, actionable structure."""
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join(str(item) for item in error.get("loc", []))
        msg = error.get("msg", "Invalid value")
        formatted_errors.append({"field": loc, "message": msg})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "type": "validation_error",
            "message": "Invalid request payload or parameters",
            "details": formatted_errors,
        },
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Standardize HTTP exception error envelopes across all endpoints."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "type": "http_error",
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions to prevent leaking tracebacks."""
    app_logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "type": "internal_server_error",
            "status_code": 500,
            "detail": "An unexpected server error occurred. Please try again later.",
        },
    )


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint — redirects to docs."""
    return {
        "service": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
