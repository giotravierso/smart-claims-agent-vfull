"""
Tests de los agentes especialistas (B, C, D, G) y del Claim Resolver (E).
Como reason() hace fallback determinista sin ANTHROPIC_API_KEY, estos
tests son rapidos y no requieren red.
"""
import os

import pytest

from app.agents.claim_resolver       import claim_resolver_node
from app.agents.coverage_checker     import coverage_checker_node
from app.agents.document_validator   import document_validator_node
from app.agents.fraud_compliance     import fraud_compliance_node
from app.agents.multimodal_extractor import multimodal_extractor_node


# Asegura que reason() use el fallback (sin clave de API)
os.environ.pop("ANTHROPIC_API_KEY", None)


BASE = {
    "claim_id":         "CLM-X",
    "client_id":        "C-1",
    "client_email":     "test@test.com",
    "claim_type":       "danys_propis",
    "amount_requested": 3200.0,
    "documents":        ["foto_danys", "factura", "denuncia_companyia"],
    "reasoning_trace":  [],
    "decisions_log":    [],
}


# ── Agente B — Document Validator ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_b_validates_complete_docs():
    out = await document_validator_node(dict(BASE))
    assert out["validation_result"]["is_valid"] is True
    assert out["decisions_log"][0]["agent"] == "agent_b_document_validator"
    assert out["decisions_log"][0]["action"] == "validated"


@pytest.mark.asyncio
async def test_agent_b_detects_missing_docs():
    state = dict(BASE)
    state["documents"] = ["foto_danys"]  # faltan factura y denuncia_companyia
    out = await document_validator_node(state)
    assert out["validation_result"]["is_valid"] is False
    assert "factura" in out["validation_result"]["missing_docs"]
    assert out["decisions_log"][0]["action"] == "info_requested"


@pytest.mark.asyncio
async def test_agent_b_unknown_type_uses_default():
    state = dict(BASE)
    state["claim_type"] = "tipo_inexistente"
    state["documents"]  = ["foto_danys", "factura"]
    out = await document_validator_node(state)
    assert out["validation_result"]["is_valid"] is True


# ── Agente G — Fraud Compliance ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_g_returns_fraud_check():
    out = await fraud_compliance_node(dict(BASE))
    assert "risk_score" in out["fraud_result"]
    assert 0.0 <= out["fraud_result"]["risk_score"] <= 1.0
    assert out["decisions_log"][0]["agent"] == "agent_g_fraud_compliance"


# ── Agente C — Multimodal Extractor ───────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_c_extracts_with_confidence():
    out = await multimodal_extractor_node(dict(BASE))
    assert "by_document" in out["extraction_result"]
    assert len(out["extraction_result"]["by_document"]) == 3
    assert 0.0 <= out["extraction_result"]["avg_confidence"] <= 1.0


# ── Agente D — Coverage Checker ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_d_covers_danys_propis():
    out = await coverage_checker_node(dict(BASE))
    assert out["coverage_result"]["covered"] is True


@pytest.mark.asyncio
async def test_agent_d_no_coverage_for_mechanical():
    state = dict(BASE)
    state["claim_type"] = "danys_mecanics"
    out = await coverage_checker_node(state)
    assert out["coverage_result"]["covered"] is False


# ── Agente E — Claim Resolver ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_e_approves_payment_low_amount():
    state = dict(BASE)
    state["coverage_result"] = {
        "covered":        True,
        "net_payable":    2900.0,
        "policy_section": "SP-PCS-009 § 3.2",
    }
    out = await claim_resolver_node(state)
    assert out["decision"] == "PAGO"
    assert out["status"]   == "resolved"
    assert out["resolution"]["amount_paid"] == 2900.0


@pytest.mark.asyncio
async def test_agent_e_routes_hitl_high_amount():
    state = dict(BASE)
    state["coverage_result"] = {
        "covered":        True,
        "net_payable":    9000.0,
        "policy_section": "SP-PCS-009 § 4.1",
    }
    out = await claim_resolver_node(state)
    assert out["decision"]      == "REVISION_HUMANA"
    assert out["hitl_required"] is True


@pytest.mark.asyncio
async def test_agent_e_rejects_no_coverage():
    state = dict(BASE)
    state["coverage_result"] = {
        "covered":        False,
        "net_payable":    0.0,
        "policy_section": "SP-PCS-009 § 7.3",
    }
    out = await claim_resolver_node(state)
    assert out["decision"] == "RECHAZO"
    assert out["status"]   == "rejected"
