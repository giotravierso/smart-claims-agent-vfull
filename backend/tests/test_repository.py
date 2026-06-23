import pytest


@pytest.mark.asyncio
async def test_log_and_read_decision(seed_claim):
    from app.db.repository import log_agent_decision, get_claim_with_decisions
    await log_agent_decision(seed_claim, "agent_g", "check_fraud",
                             "Riesgo bajo, sin coincidencia OFAC", confidence=0.95)
    claim = await get_claim_with_decisions(seed_claim)
    assert claim is not None
    assert len(claim["decisions"]) == 1
    assert claim["decisions"][0]["agent"] == "agent_g"
    assert claim["decisions"][0]["confidence"] == 0.95


@pytest.mark.asyncio
async def test_get_unknown_claim_returns_none(test_db):
    from app.db.repository import get_claim_with_decisions
    assert await get_claim_with_decisions("NOPE") is None


@pytest.mark.asyncio
async def test_save_claim_is_idempotent(test_db):
    from app.db.repository import save_claim, get_claim_with_decisions
    await save_claim("CLM-X", "C", "robatori", amount_requested=100.0)
    await save_claim("CLM-X", "C", "robatori", amount_requested=100.0)
    claim = await get_claim_with_decisions("CLM-X")
    assert claim["claim_id"] == "CLM-X"
