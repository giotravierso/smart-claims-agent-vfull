"""
Fraud Compliance — Agente G del sistema Smart-Claims de Seguros Pepin.

Responsabilidad unica: cribado del cliente contra listas restrictivas
(OFAC, ONU) y calculo del score de fraude. Se invoca como filtro de
ENTRADA, no como filtro de salida, alineado con la politica corporativa
PEPIN-POL-CP-0006.

Si is_flagged=True, el supervisor cortara el flujo y derivara a HITL.

Referencia en la memoria del TFM: Agente G (fraud_compliance.py).
"""
from __future__ import annotations

import logging

from app.agents.reasoning import reason
from app.tools.claim_tools import check_fraud

logger = logging.getLogger(__name__)


async def fraud_compliance_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente G — Fraud Compliance.

    Lee del estado:    claim_id, client_id, amount_requested.
    Escribe en estado: fraud_result, reasoning_trace, decisions_log.
    """
    claim_id  = state["claim_id"]
    client_id = state.get("client_id", "desconocido")
    amount    = state.get("amount_requested") or 0.0

    logger.info(
        "[Agente G — FraudCompliance] Inicio — expediente %s | cliente: %s | importe: %.2f EUR",
        claim_id, client_id, amount,
    )

    # ── Comprobacion determinista (mock OFAC + score) ────────────────────
    result = check_fraud.invoke({
        "claim_id":  claim_id,
        "client_id": client_id,
        "amount":    amount,
    })

    # ── Razonamiento (LLM opcional con fallback determinista) ────────────
    fallback = (
        f"Agente G: riesgo de fraude {result['risk_score']:.2f}. "
        f"{'MARCADO para revision humana' if result['is_flagged'] else 'sin indicios relevantes'}. "
        f"Indicadores: {', '.join(result['fraud_indicators']) if result['fraud_indicators'] else 'ninguno'}."
    )

    reasoning = reason(
        system=(
            "Eres el Agente G (Fraud Compliance) del sistema Smart-Claims "
            "de Seguros Pepin. Tu rol es el cribado contra listas OFAC/ONU "
            "y el calculo del score de fraude. Justifica el resultado de "
            "forma tecnica y concisa. Responde siempre en castellano."
        ),
        prompt=(
            f"Resultado del cribado antifraude:\n"
            f"- Expediente: {claim_id}\n"
            f"- Cliente (hash): {result['client_id_hash']}\n"
            f"- Importe: {amount} EUR\n"
            f"- Score de riesgo: {result['risk_score']}\n"
            f"- OFAC match: {result['ofac_match']}\n"
            f"- Indicadores: {result['fraud_indicators']}\n"
            f"- Marcado: {result['is_flagged']}\n\n"
            f"Justifica el resultado del cribado."
        ),
        fallback=fallback,
    )

    logger.info(
        "[Agente G] Cribado completado — is_flagged=%s | risk=%.3f",
        result["is_flagged"], result["risk_score"],
    )

    update = {
        "fraud_result":    result,
        "reasoning_trace": [reasoning],
        "decisions_log":   [{
            "agent":         "agent_g_fraud_compliance",
            "action":        "blocked" if result["is_flagged"] else "cleared",
            "reasoning":     reasoning,
            "confidence":    None,
            "hitl_required": bool(result["is_flagged"]),
        }],
    }

    # Si el cribado bloquea, el supervisor terminara el flujo
    if result["is_flagged"]:
        update["terminate"]          = True
        update["termination_reason"] = "caso bloqueado por fraude/OFAC"

    return update
