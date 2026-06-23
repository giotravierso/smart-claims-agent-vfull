import pytest

from app.agents.specialists import (
    agent_b_validate,
    agent_c_extract,
    agent_d_policy,
    agent_g_fraud,
)

BASE = {"claim_id": "CLM-X", "client_id": "C-1", "claim_type": "danys_propis",
        "amount_requested": 3200.0, "doc_types": ["foto_danys", "factura", "acta_policial"],
        "reasoning_trace": [], "decisions_log": []}


@pytest.mark.asyncio
async def test_agent_b_validates_complete_docs():
    out = await agent_b_validate(dict(BASE))
    assert out["validation"]["is_valid"] is True
    assert out["decisions_log"][0]["agent"] == "agent_b"


@pytest.mark.asyncio
async def test_agent_b_detects_missing_docs():
    state = dict(BASE); state["doc_types"] = ["factura"]
    out = await agent_b_validate(state)
    assert out["validation"]["is_valid"] is False
    assert "acta_policial" in out["validation"]["missing_docs"]


@pytest.mark.asyncio
async def test_agent_c_extracts_with_confidence():
    out = await agent_c_extract(dict(BASE))
    assert "extracted" in out["extraction"]
    assert 0.0 <= out["decisions_log"][0]["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_agent_d_marks_coverage():
    out = await agent_d_policy(dict(BASE))
    assert out["policy_check"]["covered"] is True
    assert out["decisions_log"][0]["agent"] == "agent_d"


@pytest.mark.asyncio
async def test_agent_d_no_coverage_for_mechanical():
    state = dict(BASE); state["claim_type"] = "danys_mecànics"
    out = await agent_d_policy(state)
    assert out["policy_check"]["covered"] is False


@pytest.mark.asyncio
async def test_agent_g_returns_fraud_check():
    out = await agent_g_fraud(dict(BASE))
    assert "risk_score" in out["fraud_check"]
    assert out["decisions_log"][0]["agent"] == "agent_g"
