"""Database engine, session factory, and base model.

Uses async SQLAlchemy 2.0 with asyncpg driver for PostgreSQL.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# ── Async Engine (FastAPI) ──
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# ── Async Session Factory ──
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Sync Engine (Celery Workers & Sync Utilities) ──
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

# ── Sync Session Factory ──
sync_session_factory = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)


# ── Declarative Base ──
class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_db() -> AsyncSession:
    """Dependency that yields an async database session and closes it after use."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@contextmanager
def get_sync_db():
    """Context manager yielding a synchronous database session for Celery tasks."""
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

