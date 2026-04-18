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
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
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


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Make SQLite more resilient under concurrent UI polling + writes."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


async def create_tables() -> None:
    """Create all tables defined in models. Called on app startup."""
    async with engine.begin() as conn:
        from models import Transaction, Inventory, DailySummary  # noqa: F401 — import to register models
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_sqlite_schema)
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


def _ensure_sqlite_schema(sync_conn) -> None:
    table_columns = {
        "inventory": ["last_sale_price", "created_at"],
        "daily_summaries": ["top_selling_quantity"],
    }

    for table_name, column_names in table_columns.items():
        result = sync_conn.exec_driver_sql(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in result.fetchall()}
        for column_name in column_names:
            if column_name not in existing_columns:
                logger.info("Applying compatibility migration for %s.%s", table_name, column_name)
                if table_name == "inventory" and column_name == "last_sale_price":
                    sync_conn.exec_driver_sql(
                        "ALTER TABLE inventory ADD COLUMN last_sale_price FLOAT"
                    )
                elif table_name == "inventory" and column_name == "created_at":
                    sync_conn.exec_driver_sql(
                        "ALTER TABLE inventory ADD COLUMN created_at DATETIME"
                    )
                    sync_conn.exec_driver_sql(
                        "UPDATE inventory SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
                    )
                elif table_name == "daily_summaries" and column_name == "top_selling_quantity":
                    sync_conn.exec_driver_sql(
                        "ALTER TABLE daily_summaries ADD COLUMN top_selling_quantity FLOAT"
                    )
