"""Repositori de persistència per a sinistres i decisions d'agents.

Accedeix a AsyncSessionLocal a través de l'atribut del mòdul (db_session.AsyncSessionLocal)
per permetre que els tests substitueixin la sessió per una de SQLite en memòria.
"""

from sqlalchemy import select

from app.db import session as db_session
from app.db.models import AgentDecision, Claim, ClaimStatus


async def save_claim(
    claim_id: str,
    client_id: str,
    claim_type: str,
    channel: str = "email",
    amount_requested: float | None = None,
    status: ClaimStatus = ClaimStatus.OPEN,
) -> None:
    """Insereix un sinistre si no existeix; si ja existeix, el deixa intacte (upsert idempotent)."""
    async with db_session.AsyncSessionLocal() as s:
        existing = await s.get(Claim, claim_id)
        if existing is None:
            s.add(
                Claim(
                    id=claim_id,
                    client_id=client_id,
                    claim_type=claim_type,
                    channel=channel,
                    amount_requested=amount_requested,
                    status=status,
                )
            )
            await s.commit()


async def log_agent_decision(
    claim_id: str,
    agent: str,
    action: str,
    reasoning: str,
    confidence: float | None = None,
    hitl_required: bool = False,
) -> int:
    """Insereix una decisió d'agent i retorna el seu id generat."""
    async with db_session.AsyncSessionLocal() as s:
        decision = AgentDecision(
            claim_id=claim_id,
            agent=agent,
            action=action,
            reasoning=reasoning,
            confidence=confidence,
            hitl_required=hitl_required,
        )
        s.add(decision)
        await s.commit()
        await s.refresh(decision)
        return decision.id


async def get_claim_with_decisions(claim_id: str) -> dict | None:
    """Retorna un dict pla amb el sinistre i les seves decisions, o None si no existeix."""
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
            "claim_id": claim.id,
            "client_id": claim.client_id,
            "claim_type": claim.claim_type,
            "channel": claim.channel,
            "status": claim.status,
            "amount_requested": claim.amount_requested,
            "amount_approved": claim.amount_approved,
            "decisions": [
                {
                    "id": d.id,
                    "agent": d.agent,
                    "action": d.action,
                    "reasoning": d.reasoning,
                    "confidence": d.confidence,
                    "hitl_required": d.hitl_required,
                }
                for d in decisions
            ],
        }
