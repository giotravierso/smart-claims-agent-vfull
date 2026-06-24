"""
Fixtures comunes a todos los tests.

Sustituye la sesion async de produccion (aiomysql/MariaDB) por una de
SQLite en memoria. Esto permite que los tests sean rapidos, reproducibles
y no requieran levantar Docker.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db          import session as db_session
from app.db.session  import Base
from app.db          import models  # noqa: F401 — registra las tablas en Base.metadata


@pytest_asyncio.fixture
async def test_db(monkeypatch):
    """SQLite async en memoria; sustituye AsyncSessionLocal de la app."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "AsyncSessionLocal", TestSession)

    yield TestSession

    await engine.dispose()


@pytest_asyncio.fixture
async def seed_claim(test_db):
    """Inserta un expediente de prueba y devuelve su id."""
    from app.db.repository import save_claim

    await save_claim(
        claim_id         = "CLM-TEST",
        client_id        = "CLIENT-T",
        claim_type       = "danys_propis",
        channel          = "email",
        amount_requested = 3200.0,
    )
    return "CLM-TEST"
