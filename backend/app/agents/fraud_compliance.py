"""
Fraud Compliance — Agente G del sistema Smart-Claims de Seguros Pepin.

Combina cuatro detectores deterministas:
  1. Verificacion OFAC/ONU contra lista de sanciones (fuzzy matching).
  2. Anomalia de importe segun Z-score sobre baselines por tipo.
  3. Duplicados recientes en ventana de 90 dias.
  4. Coherencia documental entre fechas de documentos.

Emite un veredicto graduado: CLEAR / MEDIUM_RISK / HIGH_RISK / BLOCKED.
Si is_flagged=True (HIGH_RISK o BLOCKED), el supervisor cortara el flujo.

Referencia en la memoria del TFM: Agente G (fraud_compliance.py).
"""
from __future__ import annotations

import logging

from app.agents.reasoning import reason
from app.tools.fraud_tools import (
    check_amount_anomaly,
    check_document_coherence,
    check_duplicate_claims,
    check_ofac_sanctions,
    compute_risk_score,
)

logger = logging.getLogger(__name__)


# Mock de historial de reclamaciones para detector de duplicados.
# En produccion seria una consulta async a MariaDB sobre la tabla `claims`.
_MOCK_CLAIM_HISTORY: list[dict] = [
    {"id": "CLM-H001", "client_id": "C-A", "claim_type": "danys_propis",    "created_at": "2026-05-20"},
    {"id": "CLM-H002", "client_id": "C-B", "claim_type": "responsabilitat", "created_at": "2026-04-15"},
    {"id": "CLM-H003", "client_id": "C-C", "claim_type": "robatori",        "created_at": "2026-03-10"},
]


async def fraud_compliance_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente G — Fraud Compliance.

    Lee del estado:    claim_id, client_id, claim_type, amount_requested,
                       client_name (opcional), extraction_result (opcional).
    Escribe en estado: fraud_result, reasoning_trace, decisions_log.
    """
    claim_id    = state["claim_id"]
    client_id   = state.get("client_id", "desconocido")
    client_name = state.get("client_name", client_id)
    claim_type  = state.get("claim_type") or "default"
    amount      = float(state.get("amount_requested") or 0.0)
    extracted   = state.get("extraction_result") or {}

    logger.info(
        "[Agente G — FraudCompliance] Inicio — expediente %s | cliente: %s | importe: %.2f EUR",
        claim_id, client_id, amount,
    )

    # ── Ejecutar los cuatro detectores ────────────────────────────────────
    ofac      = check_ofac_sanctions(client_name)
    amount_ck = check_amount_anomaly(claim_type, amount)
    duplicate = check_duplicate_claims(client_id, claim_type, _MOCK_CLAIM_HISTORY)
    doc_check = check_document_coherence(extracted)

    risk_score, verdict = compute_risk_score(ofac, amount_ck, duplicate, doc_check)
    is_flagged = verdict in ("HIGH_RISK", "BLOCKED")

    # ── Construir lista de senales activas ───────────────────────────────
    signals: list[str] = []
    if ofac.matched:
        signals.append(
            f"OFAC match: {ofac.entity_name} (lista {ofac.sanction_list}, "
            f"similitud {ofac.similarity:.1%})"
        )
    if amount_ck.flagged:
        reason_amount = "supera el maximo legitimo" if amount_ck.exceeded_max else f"Z-score {amount_ck.z_score}"
        signals.append(
            f"Importe anomalo: {amount:.2f} EUR ({reason_amount}; "
            f"media historica {claim_type} {amount_ck.mean:.2f} EUR)"
        )
    if duplicate.found:
        signals.append(
            f"Duplicado detectado: {duplicate.matching_claim_ids} "
            f"hace {duplicate.days_since_last} dias"
        )
    if doc_check.incoherent:
        signals.append(f"Incoherencia documental: {', '.join(doc_check.issues)}")

    if not signals:
        signals.append("Sin senales de fraude detectadas.")

    # ── Razonamiento (LLM opcional con fallback determinista) ────────────
    fallback = (
        f"Agente G: veredicto {verdict} (score {risk_score:.2f}). "
        f"{'MARCADO para revision humana.' if is_flagged else 'Sin indicios relevantes.'} "
        f"Senales activas: {'; '.join(signals)}."
    )

    reasoning = reason(
        system=(
            "Eres el Agente G (Fraud Compliance) del sistema Smart-Claims de "
            "Seguros Pepin. Tu rol es el cribado contra listas OFAC/ONU, la "
            "deteccion de importes anomalos, duplicados e incoherencias "
            "documentales. Justifica el resultado del cribado de forma "
            "tecnica y auditable. Responde siempre en castellano."
        ),
        prompt=(
            f"Resultado del cribado antifraude:\n"
            f"- Expediente: {claim_id}\n"
            f"- Cliente: {client_id} (nombre evaluado: '{client_name}')\n"
            f"- Tipo de siniestro: {claim_type}\n"
            f"- Importe: {amount} EUR\n"
            f"- Score de riesgo: {risk_score}\n"
            f"- Veredicto: {verdict}\n"
            f"- Senales activas:\n  - " + "\n  - ".join(signals) + "\n\n"
            f"Redacta un razonamiento de auditoria (4-6 frases) que explique "
            f"que senales se han activado, como se compone el score y por "
            f"que se emite este veredicto."
        ),
        fallback=fallback,
    )

    logger.info(
        "[Agente G] Cribado completado — verdict=%s | risk=%.3f | flagged=%s",
        verdict, risk_score, is_flagged,
    )

    # ── Construir resultado estructurado para el estado ──────────────────
    fraud_result = {
        "claim_id":         claim_id,
        "verdict":          verdict,
        "risk_score":       risk_score,
        "is_flagged":       is_flagged,
        "ofac_match":       ofac.matched,
        "ofac_entity":      ofac.entity_name,
        "fraud_indicators": signals if signals != ["Sin senales de fraude detectadas."] else [],
        "signals": {
            "ofac": {
                "matched":    ofac.matched,
                "entity":     ofac.entity_name,
                "similarity": ofac.similarity,
                "list":       ofac.sanction_list,
            },
            "amount": {
                "flagged":      amount_ck.flagged,
                "z_score":      amount_ck.z_score,
                "exceeded_max": amount_ck.exceeded_max,
                "mean":         amount_ck.mean,
            },
            "duplicate": {
                "found":           duplicate.found,
                "matching_claims": duplicate.matching_claim_ids,
                "days_since_last": duplicate.days_since_last,
            },
            "document": {
                "incoherent": doc_check.incoherent,
                "issues":     doc_check.issues,
            },
        },
    }

    update = {
        "fraud_result":    fraud_result,
        "reasoning_trace": [reasoning],
        "decisions_log":   [{
            "agent":         "agent_g_fraud_compliance",
            "action":        f"verdict_{verdict.lower()}",
            "reasoning":     reasoning,
            "confidence":    None,
            "hitl_required": is_flagged,
        }],
    }

    # Si el cribado bloquea o marca como alto riesgo, el supervisor termina el flujo
    if is_flagged:
        update["terminate"]          = True
        update["termination_reason"] = f"caso bloqueado por fraude (veredicto: {verdict})"

    return update
