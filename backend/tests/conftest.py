import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import session as db_session
from app.db.session import Base
from app.db import models  # noqa: F401 — registra les taules a Base.metadata


@pytest_asyncio.fixture
async def test_db(monkeypatch):
    """SQLite en memòria async; substitueix AsyncSessionLocal de l'app."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "AsyncSessionLocal", TestSession)
    yield TestSession
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_claim(test_db):
    """Insereix una sinistre de prova i retorna el seu id."""
    from app.db.repository import save_claim
    await save_claim("CLM-TEST", "CLIENT-T", "danys_propis",
                     channel="email", amount_requested=3200.0)
    return "CLM-TEST"
