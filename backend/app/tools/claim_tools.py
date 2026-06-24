"""
Mock APIs simuladas para el prototipo Smart-Claims Agent.

Cada función simula una llamada a un sistema externo real (core asegurador,
pasarela de pago, sistema de notificaciones, listas OFAC). En la Fase II
de producción se sustituirán por integraciones reales con los sistemas de
Seguros Pepín. La estructura `@tool` de LangChain permite que los agentes
las invoquen directamente y registra automáticamente la firma y docstring.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ── Documentos requeridos por tipo de siniestro ───────────────────────────
# Esta tabla se usa también en el Agente B; se expone como constante para
# que ambos (tool y agente) compartan la misma fuente de verdad.

REQUIRED_DOCS_BY_TYPE: dict[str, list[str]] = {
    "danys_propis":    ["foto_danys", "factura", "denuncia_companyia"],
    "responsabilitat": ["foto_danys", "acta_policial", "dades_tercer"],
    "robatori":        ["acta_policial", "llista_objectes_robats"],
    "danys_mecanics":  ["informe_taller", "factura"],
    "default":         ["foto_danys", "factura"],
}


# ── Tools que invocan los agentes ─────────────────────────────────────────

@tool
def validate_documents(claim_id: str, claim_type: str, doc_types: list[str]) -> dict:
    """
    Valida que la reclamación contiene todos los documentos requeridos
    para el tipo de siniestro indicado.

    Args:
        claim_id:   Identificador del expediente.
        claim_type: Tipo de siniestro (danys_propis, responsabilitat, etc.).
        doc_types:  Documentos aportados por el cliente.

    Returns:
        is_valid (bool), missing_docs (list[str]), required_docs (list[str]),
        contract_active (bool), checked_at (str ISO).
    """
    required = REQUIRED_DOCS_BY_TYPE.get(claim_type, REQUIRED_DOCS_BY_TYPE["default"])
    provided = set(doc_types or [])
    missing  = [d for d in required if d not in provided]

    return {
        "claim_id":        claim_id,
        "claim_type":      claim_type,
        "is_valid":        len(missing) == 0,
        "missing_docs":    missing,
        "required_docs":   required,
        "provided_docs":   list(provided),
        "contract_active": True,
        "checked_at":      datetime.utcnow().isoformat(),
    }


@tool
def extract_multimodal(claim_id: str, file_url: str, doc_type: str) -> dict:
    """
    Extrae datos estructurados de un documento o imagen mediante VLM.

    En producción invocaría a Claude Vision sobre los adjuntos reales
    (facturas, fotos de daños, actas policiales). La versión mock devuelve
    datos plausibles con una puntuación de confianza simulada.
    """
    mock_data = {
        "factura":         {"amount": round(random.uniform(500, 8000), 2),
                            "date":   "2026-05-10",
                            "vendor": "Taller Martinez"},
        "foto_danys":      {"damage_type": "colision frontal",
                            "severity": "moderado",
                            "estimated_repair": 3200},
        "acta_policial":   {"incident_date": "2026-05-08",
                            "parties": 2,
                            "fault_party": "tercero"},
        "denuncia_companyia": {"reported_at": "2026-05-09",
                               "incident_summary": "Colision en parking"},
        "informe_taller":  {"diagnosis": "Averia transmision",
                            "estimated_cost": 1800},
        "dades_tercer":    {"third_party_id": "X123456",
                            "insurer": "Otra aseguradora"},
        "llista_objectes_robats": {"items_count": 5, "estimated_value": 1500},
    }

    data = mock_data.get(doc_type, {"info": "documento no reconocido"})
    return {
        "claim_id":    claim_id,
        "doc_type":    doc_type,
        "extracted":   data,
        "confidence":  round(random.uniform(0.82, 0.98), 3),
        "model":       "claude-sonnet-4-6 (mock)",
        "extracted_at": datetime.utcnow().isoformat(),
    }


@tool
def check_policy(claim_id: str, claim_type: str, amount: float) -> dict:
    """
    Consulta la base de conocimiento (RAG en fase posterior) para verificar
    cobertura, limite maximo y franquicia segun el tipo de siniestro.

    Returns:
        covered (bool), max_coverage (float), deductible (float),
        net_payable (float), policy_section (str).
    """
    coverage_rules = {
        "danys_propis":    {"covered": True,  "max": 10000, "deductible": 300,
                            "section": "SP-PCS-009 § 3.2"},
        "responsabilitat": {"covered": True,  "max": 50000, "deductible": 0,
                            "section": "SP-PCS-009 § 4.1"},
        "robatori":        {"covered": True,  "max": 8000,  "deductible": 500,
                            "section": "SP-PCS-009 § 5.0"},
        "danys_mecanics":  {"covered": False, "max": 0,     "deductible": 0,
                            "section": "SP-PCS-009 § 7.3 (exclusion)"},
    }

    rule = coverage_rules.get(claim_type, {
        "covered": False, "max": 0, "deductible": 0,
        "section": "tipo no catalogado",
    })

    net_payable = (
        max(0, min(amount, rule["max"]) - rule["deductible"])
        if rule["covered"] else 0.0
    )

    return {
        "claim_id":         claim_id,
        "claim_type":       claim_type,
        "amount_requested": amount,
        "covered":          rule["covered"],
        "max_coverage":     rule["max"],
        "deductible":       rule["deductible"],
        "net_payable":      net_payable,
        "policy_section":   rule["section"],
    }


@tool
def check_fraud(claim_id: str, client_id: str, amount: float) -> dict:
    """
    Verifica al cliente contra listas OFAC/ONU y calcula un score de fraude.
    En produccion consultaria un servicio corporativo de AML/sancions.
    El mock genera un riesgo aleatorio bajo para que algunos casos se
    marquen y se pueda demostrar el corte temprano del flujo.
    """
    risk_score = round(random.uniform(0.01, 0.35), 3)

    return {
        "claim_id":          claim_id,
        "client_id_hash":    hash(client_id) % 100000,
        "is_flagged":        risk_score > 0.30,
        "risk_score":        risk_score,
        "ofac_match":        False,
        "fraud_indicators":  [] if risk_score < 0.25 else ["importe_inusual"],
        "checked_at":        datetime.utcnow().isoformat(),
    }


@tool
def approve_payment(claim_id: str, amount: float, iban: str) -> dict:
    """Simula la emision de una transferencia de pago al cliente."""
    logger.info("MOCK PAYMENT — Expediente %s: %.2f EUR -> ****%s",
                claim_id, amount, iban[-4:])
    return {
        "claim_id":       claim_id,
        "transaction_id": f"TXN-{claim_id}-{random.randint(10000, 99999)}",
        "amount":         amount,
        "iban_last4":     iban[-4:],
        "status":         "scheduled",
        "scheduled_date": "2026-06-30",
    }


@tool
def send_rejection(claim_id: str, reason: str, client_email: str) -> dict:
    """Simula el envio de un email de rechazo justificado al cliente."""
    logger.info("MOCK REJECTION — Expediente %s -> %s", claim_id, client_email)
    return {
        "claim_id":       claim_id,
        "email_id":       f"EMAIL-{claim_id}-REJ",
        "sent_to":        client_email,
        "reason_summary": reason[:200],
        "sent_at":        datetime.utcnow().isoformat(),
    }


@tool
def request_more_info(claim_id: str, missing_fields: list[str], client_email: str) -> dict:
    """Solicita informacion adicional al cliente para poder continuar."""
    logger.info("MOCK INFO REQUEST — Expediente %s: %s", claim_id, missing_fields)
    return {
        "claim_id":         claim_id,
        "request_id":       f"INFO-{claim_id}-{random.randint(100, 999)}",
        "fields_requested": missing_fields,
        "sent_to":          client_email,
        "deadline_days":    10,
        "sent_at":          datetime.utcnow().isoformat(),
    }


# ── Conjunto exportable ───────────────────────────────────────────────────

AGENT_TOOLS = [
    validate_documents,
    extract_multimodal,
    check_policy,
    check_fraud,
    approve_payment,
    send_rejection,
    request_more_info,
]
