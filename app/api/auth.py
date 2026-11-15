"""Authentication endpoints — register, login, profile, account deletion."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_current_user
from app.core.rate_limiter import check_ip_rate_limit
from app.core.security import hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.ats_check import AtsCheckResult
from app.models.cover_letter import CoverLetter
from app.models.job import JobDescription
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.resume_document import ResumeDocument
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, UserUpdate, Token

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await check_ip_rate_limit(request, "auth", settings.auth_rate_limit_per_minute)
    """Create a new user account.

    - Validates email uniqueness
    - Hashes password with bcrypt
    - Returns user data (no password)
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get JWT token",
)
async def login(user_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    await check_ip_rate_limit(request, "auth", settings.auth_rate_limit_per_minute)
    """Authenticate user and return a JWT access token.

    - Verifies email exists
    - Verifies password against stored hash
    - Returns signed JWT with user ID as subject
    """
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current logged in user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user



@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the current user's profile (name)",
)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.name is not None:
        current_user.name = payload.name.strip() or None
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the current user's account and ALL their data",
)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Privacy-critical (Phase 8): deleting an account deletes everything —
    matches, ATS checks, cover letters, builder documents, resumes, jobs —
    in one transaction. Resumes are PII; there is no soft-delete limbo.
    Order respects the FK graph (children before parents).
    """
    uid = current_user.id
    await db.execute(delete(MatchResult).where(MatchResult.user_id == uid))
    await db.execute(delete(AtsCheckResult).where(AtsCheckResult.user_id == uid))
    await db.execute(delete(CoverLetter).where(CoverLetter.user_id == uid))
    await db.execute(delete(ResumeDocument).where(ResumeDocument.user_id == uid))
    await db.execute(delete(Resume).where(Resume.user_id == uid))
    await db.execute(delete(JobDescription).where(JobDescription.user_id == uid))
    await db.execute(delete(User).where(User.id == uid))
    await db.commit()
