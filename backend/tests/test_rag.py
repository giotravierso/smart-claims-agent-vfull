"""Tests del RAG real de pólizas (Agente D)."""
import pytest


@pytest.fixture
def rag_on(monkeypatch):
    monkeypatch.setenv("SCA_RAG_ENABLED", "1")


def test_retrieve_policy_matches_each_type(rag_on):
    from app.rag.policy_store import retrieve_policy
    cases = {
        "danys_mecanics":  ("averia del motor por desgaste", False),
        "danys_propis":    ("colision frontal de mi coche", True),
        "robatori":        ("me han robado el vehiculo", True),
        "responsabilitat": ("dano a un tercero con el coche", True),
    }
    first = retrieve_policy("danys_propis", "colision")
    if first is None:
        pytest.skip("RAG no disponible (ChromaDB o red ausentes)")
    for claim_type, (desc, expected_covered) in cases.items():
        r = retrieve_policy(claim_type, desc)
        assert r is not None
        assert r["claim_type"] == claim_type, f"recuperó {r['claim_type']} para {claim_type}"
        assert r["covered"] is expected_covered


@pytest.mark.asyncio
async def test_agent_d_uses_rag_and_computes_coverage(rag_on):
    from app.agents.coverage_checker import coverage_checker_node
    state = {"claim_id": "CLM-RAG", "claim_type": "danys_propis", "amount_requested": 3200.0}
    out = await coverage_checker_node(state)
    cov = out["coverage_result"]
    if cov.get("source") != "rag":
        pytest.skip("RAG no activo en este entorno")
    assert cov["covered"] is True
    assert cov["net_payable"] == 2900.0          # min(3200, 10000) - 300
    assert "SP-PCS-009" in cov["policy_section"]


@pytest.mark.asyncio
async def test_agent_d_fallback_to_mock_when_rag_disabled():
    # Sin SCA_RAG_ENABLED → camino mock (check_policy)
    from app.agents.coverage_checker import coverage_checker_node
    state = {"claim_id": "CLM-MOCK", "claim_type": "robatori", "amount_requested": 1000.0}
    out = await coverage_checker_node(state)
    assert out["coverage_result"]["source"] == "mock"
    assert out["coverage_result"]["covered"] is True
