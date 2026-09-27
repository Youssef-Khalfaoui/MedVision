"""Database engine and session factory.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
SQLite args are auto-detected from the URL.

V2: Ajout pool_size, pool_recycle, pool_pre_ping pour la robustesse
    en production (PostgreSQL uniquement — SQLite ignore ces options).
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

connect_args = {}
engine_args = {
    "echo": settings.debug,
}

if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL production-grade connection pool settings
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20
    engine_args["pool_pre_ping"] = True   # detect stale connections
    engine_args["pool_recycle"] = 3600    # recycle after 1 hour

engine = create_async_engine(
    settings.database_url,
    **engine_args,
    connect_args=connect_args,
)

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_session():
    """Yield an async session for FastAPI dependency injection."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
