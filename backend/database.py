"""
Susu Books - Database Setup
SQLite via SQLAlchemy with async support using aiosqlite.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event
from typing import AsyncGenerator
import logging

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Convert sqlite:/// to sqlite+aiosqlite:/// for async driver
_db_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    _db_url,
    echo=settings.db_echo,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def create_tables() -> None:
    """Create all tables defined in models. Called on app startup."""
    async with engine.begin() as conn:
        from models import Transaction, Inventory, DailySummary  # noqa: F401 — import to register models
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
