from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer

from .config import load_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


settings = load_settings()

# Для SQLite используем async-драйвер aiosqlite
if settings.db.url.startswith("sqlite:///"):
    async_db_url = settings.db.url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    async_db_url = settings.db.url

engine = create_async_engine(async_db_url, echo=False, future=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with SessionFactory() as session:
        yield session


async def init_db() -> None:
    """Создать таблицы, если их ещё нет (простая инициализация без Alembic)."""
    from . import models  # noqa: F401 - ensure models are imported

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)








