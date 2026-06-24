"""
Endpoints REST para la gestion de reclamaciones.

POST  /api/v1/claims/                   - crea y procesa una reclamacion
GET   /api/v1/claims/                   - lista reclamaciones
GET   /api/v1/claims/{claim_id}         - detalle con decisiones
GET   /api/v1/claims/{claim_id}/trace   - solo Chain of Thought
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.agents.orchestrator import process_claim
from app.db.repository       import get_claim_with_decisions, list_claims
from app.schemas.claims      import (
    AgentDecisionItem,
    ClaimCreateRequest,
    ClaimListItem,
    ClaimResponse,
    ClaimTraceResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ── POST /api/v1/claims/ ──────────────────────────────────────────────────

@router.post("/", response_model=ClaimResponse, status_code=201)
async def create_and_process_claim(request: ClaimCreateRequest) -> ClaimResponse:
    """
    Crea una nueva reclamacion y la procesa a traves del sistema agentico.
    El orquestador (Agente A) coordina la ejecucion de los agentes
    especialistas (B, C, D, E, G) hasta llegar a una decision final.
    """
    claim_id = request.claim_id or f"CLM-{uuid.uuid4().hex[:8].upper()}"
    logger.info("[API] Nueva reclamacion %s | cliente: %s | tipo: %s",
                claim_id, request.client_id, request.claim_type)

    try:
        final_state = await process_claim(
            claim_id         = claim_id,
            client_id        = request.client_id,
            claim_type       = request.claim_type,
            amount_requested = request.amount_requested,
            channel          = request.channel,
            documents        = request.documents,
            client_email     = request.client_email,
        )
    except Exception as exc:
        logger.exception("[API] Error procesando %s", claim_id)
        raise HTTPException(
            status_code = 500,
            detail      = f"Error procesando la reclamacion: {exc}",
        )

    resolution = final_state.get("resolution") or {}

    return ClaimResponse(
        claim_id           = claim_id,
        status             = str(final_state.get("status", "open")),
        decision           = final_state.get("decision") or resolution.get("decision"),
        amount_paid        = resolution.get("amount_paid"),
        amount_requested   = request.amount_requested,
        hitl_required      = bool(final_state.get("hitl_required", False)),
        termination_reason = final_state.get("termination_reason"),
        reasoning_trace    = final_state.get("reasoning_trace", []),
    )


# ── GET /api/v1/claims/{claim_id} ─────────────────────────────────────────

@router.get("/{claim_id}")
async def get_claim(claim_id: str) -> dict:
    """Devuelve el expediente con todas sus decisiones."""
    claim = await get_claim_with_decisions(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Expediente {claim_id} no encontrado")
    return claim


# ── GET /api/v1/claims/ ───────────────────────────────────────────────────

@router.get("/", response_model=list[ClaimListItem])
async def list_all_claims(
    status: str | None = Query(default=None, description="Filtrar por estado"),
    limit:  int        = Query(default=20, ge=1, le=100),
    offset: int        = Query(default=0, ge=0),
) -> list[ClaimListItem]:
    """Lista las reclamaciones con paginacion y filtro opcional por estado."""
    rows = await list_claims(status=status, limit=limit, offset=offset)
    return [ClaimListItem(**r) for r in rows]


# ── GET /api/v1/claims/{claim_id}/trace ───────────────────────────────────

@router.get("/{claim_id}/trace", response_model=ClaimTraceResponse)
async def get_claim_trace(claim_id: str) -> ClaimTraceResponse:
    """Devuelve solo el Chain of Thought de un expediente."""
    claim = await get_claim_with_decisions(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Expediente {claim_id} no encontrado")

    return ClaimTraceResponse(
        claim_id  = claim_id,
        decisions = [AgentDecisionItem(**d) for d in claim["decisions"]],
    )
