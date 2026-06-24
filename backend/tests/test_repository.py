"""
Tests de la capa de persistencia (repository).
Usan la fixture test_db con SQLite en memoria.
"""
import pytest

from app.db.models     import ClaimStatus
from app.db.repository import (
    get_claim_with_decisions,
    list_claims,
    log_agent_decision,
    save_claim,
)


@pytest.mark.asyncio
async def test_save_claim_creates_new(test_db):
    await save_claim("CLM-A", "C-1", "danys_propis", amount_requested=1000.0)
    out = await get_claim_with_decisions("CLM-A")
    assert out is not None
    assert out["claim_id"]  == "CLM-A"
    assert out["client_id"] == "C-1"


@pytest.mark.asyncio
async def test_save_claim_idempotent(test_db):
    """Guardar el mismo expediente dos veces no duplica filas."""
    await save_claim("CLM-B", "C-2", "responsabilitat", amount_requested=500.0)
    await save_claim("CLM-B", "C-2", "responsabilitat",
                     amount_requested=500.0, amount_approved=400.0,
                     status=ClaimStatus.RESOLVED)
    out = await get_claim_with_decisions("CLM-B")
    assert out["status"] == "resolved"
    assert out["amount_approved"] == 400.0


@pytest.mark.asyncio
async def test_log_agent_decision_persists(test_db):
    await save_claim("CLM-C", "C-3", "robatori")
    decision_id = await log_agent_decision(
        claim_id  = "CLM-C",
        agent     = "agent_b_document_validator",
        action    = "validated",
        reasoning = "Documentacion completa y conforme.",
    )
    assert decision_id > 0

    out = await get_claim_with_decisions("CLM-C")
    assert len(out["decisions"]) == 1
    assert out["decisions"][0]["agent"] == "agent_b_document_validator"


@pytest.mark.asyncio
async def test_get_claim_not_found(test_db):
    out = await get_claim_with_decisions("CLM-DOES-NOT-EXIST")
    assert out is None


@pytest.mark.asyncio
async def test_list_claims_paginates(test_db):
    for i in range(5):
        await save_claim(f"CLM-LST-{i}", f"C-{i}", "danys_propis")

    page1 = await list_claims(limit=3, offset=0)
    page2 = await list_claims(limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) == 2
