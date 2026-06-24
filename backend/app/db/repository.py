"""
Repositorio de persistencia para expedientes y decisiones de agentes.

Centraliza todo el acceso a la base de datos relacional. Los agentes NO
acceden directamente a la base de datos: acumulan sus contribuciones en
el estado (decisions_log) y la persistencia se realiza al final del
flujo desde process_claim.

Acceder a AsyncSessionLocal a través del atributo del módulo
(db_session.AsyncSessionLocal) permite que los tests sustituyan la sesión
por una de SQLite en memoria sin tocar el código de producción.
"""
from __future__ import annotations

from sqlalchemy import select

from app.db import session as db_session
from app.db.models import AgentDecision, Claim, ClaimStatus


# ── Escritura ─────────────────────────────────────────────────────────────

async def save_claim(
    claim_id:         str,
    client_id:        str,
    claim_type:       str,
    channel:          str = "email",
    amount_requested: float | None = None,
    amount_approved:  float | None = None,
    status:           ClaimStatus = ClaimStatus.OPEN,
) -> None:
    """
    Inserta un expediente si no existe; si ya existe, actualiza el estado
    y el importe aprobado. Operación idempotente, segura ante reintentos.
    """
    async with db_session.AsyncSessionLocal() as s:
        existing = await s.get(Claim, claim_id)

        if existing is None:
            s.add(Claim(
                id               = claim_id,
                client_id        = client_id,
                claim_type       = claim_type,
                channel          = channel,
                amount_requested = amount_requested,
                amount_approved  = amount_approved,
                status           = status,
            ))
        else:
            existing.status = status
            if amount_approved is not None:
                existing.amount_approved = amount_approved

        await s.commit()


async def log_agent_decision(
    claim_id:      str,
    agent:         str,
    action:        str,
    reasoning:     str,
    confidence:    float | None = None,
    hitl_required: bool = False,
) -> int:
    """
    Inserta una decisión de agente y devuelve el id generado.
    Es la materialización persistente del decisions_log que viaja en el
    estado del grafo.
    """
    async with db_session.AsyncSessionLocal() as s:
        decision = AgentDecision(
            claim_id      = claim_id,
            agent         = agent,
            action        = action,
            reasoning     = reasoning,
            confidence    = confidence,
            hitl_required = hitl_required,
        )
        s.add(decision)
        await s.commit()
        await s.refresh(decision)
        return decision.id


# ── Lectura ───────────────────────────────────────────────────────────────

async def get_claim_with_decisions(claim_id: str) -> dict | None:
    """
    Devuelve un diccionario plano con el expediente y todas sus decisiones
    en orden cronológico, o None si el expediente no existe.
    """
    async with db_session.AsyncSessionLocal() as s:
        claim = await s.get(Claim, claim_id)
        if claim is None:
            return None

        result = await s.execute(
            select(AgentDecision)
            .where(AgentDecision.claim_id == claim_id)
            .order_by(AgentDecision.id.asc())
        )
        decisions = result.scalars().all()

        return {
            "claim_id":         claim.id,
            "client_id":        claim.client_id,
            "claim_type":       claim.claim_type,
            "channel":          claim.channel,
            "status":           claim.status.value if hasattr(claim.status, "value") else str(claim.status),
            "amount_requested": claim.amount_requested,
            "amount_approved":  claim.amount_approved,
            "created_at":       claim.created_at.isoformat() if claim.created_at else None,
            "decisions": [
                {
                    "id":            d.id,
                    "agent":         d.agent,
                    "action":        d.action,
                    "reasoning":     d.reasoning,
                    "confidence":    d.confidence,
                    "hitl_required": d.hitl_required,
                    "created_at":    d.created_at.isoformat() if d.created_at else None,
                }
                for d in decisions
            ],
        }


async def list_claims(
    status: str | None = None,
    limit:  int        = 20,
    offset: int        = 0,
) -> list[dict]:
    """Lista expedientes con paginación y filtro opcional por estado."""
    async with db_session.AsyncSessionLocal() as s:
        query = select(Claim).order_by(Claim.created_at.desc()).limit(limit).offset(offset)
        if status:
            try:
                query = query.where(Claim.status == ClaimStatus(status))
            except ValueError:
                return []
        result = await s.execute(query)
        claims = result.scalars().all()
        return [
            {
                "id":               c.id,
                "client_id":        c.client_id,
                "claim_type":       c.claim_type,
                "status":           c.status.value if hasattr(c.status, "value") else str(c.status),
                "amount_requested": c.amount_requested,
                "amount_approved":  c.amount_approved,
                "created_at":       c.created_at.isoformat() if c.created_at else None,
            }
            for c in claims
        ]
