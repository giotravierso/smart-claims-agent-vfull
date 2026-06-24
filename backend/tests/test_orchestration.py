"""
Tests del flujo de orquestacion completo.

Cubre los 4 escenarios principales del sistema:
- Pago automatico (cobertura + importe bajo + docs completos)
- HITL (cobertura + importe alto)
- Rechazo por no cobertura
- Solicitud de informacion por documentos incompletos

Los tests usan SQLite en memoria para evitar dependencia de MariaDB.
"""
import os
import random

import pytest

from app.agents.orchestrator import process_claim


# Sin LLM externo: tests rapidos y deterministas
os.environ.pop("ANTHROPIC_API_KEY", None)

# Semilla fija para que check_fraud (mock random) sea reproducible.
random.seed(7)


FULL_DOCS = ["foto_danys", "factura", "denuncia_companyia"]


@pytest.mark.asyncio
async def test_flow_automatic_payment(test_db):
    """Cobertura OK + importe bajo + docs completos → PAGO automatico."""
    random.seed(7)
    result = await process_claim(
        claim_id         = "CLM-PAY",
        client_id        = "C-A",
        claim_type       = "danys_propis",
        amount_requested = 3200.0,
        documents        = FULL_DOCS,
    )

    assert result["status"]                  == "resolved"
    assert result["decision"]                == "PAGO"
    assert result["resolution"]["amount_paid"] is not None
    assert result["resolution"]["amount_paid"] > 0


@pytest.mark.asyncio
async def test_flow_hitl_high_amount(test_db):
    """Cobertura OK + importe alto → REVISION HUMANA."""
    random.seed(7)
    result = await process_claim(
        claim_id         = "CLM-HITL",
        client_id        = "C-B",
        claim_type       = "responsabilitat",
        amount_requested = 9500.0,
        documents        = ["foto_danys", "acta_policial", "dades_tercer"],
    )

    assert result["status"]        == "pending_review"
    assert result["decision"]      == "REVISION_HUMANA"
    assert result["hitl_required"] is True


@pytest.mark.asyncio
async def test_flow_rejection_no_coverage(test_db):
    """Tipo no cubierto → RECHAZO justificado."""
    random.seed(7)
    result = await process_claim(
        claim_id         = "CLM-REJ",
        client_id        = "C-C",
        claim_type       = "danys_mecanics",
        amount_requested = 1500.0,
        documents        = ["informe_taller", "factura"],
    )

    assert result["status"]   == "rejected"
    assert result["decision"] == "RECHAZO"


@pytest.mark.asyncio
async def test_flow_request_info_missing_docs(test_db):
    """Documentos incompletos → cliente notificado, flujo cortado."""
    random.seed(7)
    result = await process_claim(
        claim_id         = "CLM-INFO",
        client_id        = "C-D",
        claim_type       = "danys_propis",
        amount_requested = 2500.0,
        documents        = ["foto_danys"],   # faltan factura y denuncia
    )

    assert result["validation_result"]["is_valid"] is False
    assert "factura" in result["validation_result"]["missing_docs"]
    # El flujo no llega al claim_resolver
    assert result.get("resolution") is None


@pytest.mark.asyncio
async def test_decisions_log_accumulates(test_db):
    """El decisions_log debe contener una entrada por agente invocado."""
    random.seed(7)
    result = await process_claim(
        claim_id         = "CLM-LOG",
        client_id        = "C-E",
        claim_type       = "danys_propis",
        amount_requested = 2500.0,
        documents        = FULL_DOCS,
    )

    # Triage + Fraude + Docs + Extraccion + Cobertura + Resolucion = 6 entradas
    agents_invoked = [d["agent"] for d in result["decisions_log"]]
    assert "agent_a_orchestrator"           in agents_invoked
    assert "agent_b_document_validator"     in agents_invoked
    assert "agent_g_fraud_compliance"       in agents_invoked
    assert "agent_c_multimodal_extractor"   in agents_invoked
    assert "agent_d_coverage_checker"       in agents_invoked
    assert "agent_e_claim_resolver"         in agents_invoked
