"""
Punto de entrada de la API FastAPI del sistema Smart-Claims Agent.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session   import init_db
from app.routers      import agents, claims, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa el esquema de BD al arrancar (idempotente)."""
    try:
        await init_db()
        logger.info("Base de datos inicializada.")
    except Exception as exc:
        # No bloquea el arranque si MariaDB no esta disponible
        logger.warning("init_db ha fallado: %s", exc)
    yield


app = FastAPI(
    title       = "Smart-Claims Agent API",
    description = "Sistema agentico para la gestion de reclamaciones de Seguros Pepin.",
    version     = "0.5.0",
    lifespan    = lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


app.include_router(health.router,            tags=["health"])
app.include_router(claims.router, prefix="/api/v1/claims", tags=["claims"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
