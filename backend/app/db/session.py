"""
Gestión de la conexión a MariaDB.

Expone:
- engine y AsyncSessionLocal: motor y sesión async (para FastAPI y agentes).
- Base: clase declarativa base para los modelos.
- init_db: crea el esquema (idempotente).
- get_db: dependency injection async para los endpoints FastAPI.
"""
from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DB_USER     = os.getenv("DB_USER",     "claims_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "claims_dev")
DB_HOST     = os.getenv("DB_HOST",     "mariadb")
DB_PORT     = os.getenv("DB_PORT",     "3306")
DB_NAME     = os.getenv("DB_NAME",     "smart_claims")

DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """
    Crea el esquema relacional si no existe (idempotente).
    En Docker el init.sql ya crea las tablas, pero esta función cubre la
    ejecución local y los tests, manteniendo SQLAlchemy como fuente única
    de verdad del esquema.
    """
    from app.db import models  # noqa: F401 — registra las tablas en Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency injection async para los endpoints de FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
