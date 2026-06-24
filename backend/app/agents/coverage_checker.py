"""
Coverage Checker — Agente D del sistema Smart-Claims de Seguros Pepin.

Responsabilidad unica: verificar si el siniestro esta cubierto por la
poliza del cliente, consultando la base de conocimiento RAG (ChromaDB
en fase posterior).

Devuelve cobertura, limite maximo, franquicia e importe neto pagable.

Referencia en la memoria del TFM: Agente D (coverage_checker.py).
"""
from __future__ import annotations

import logging

from app.agents.reasoning import reason
from app.tools.claim_tools import check_policy

logger = logging.getLogger(__name__)


async def coverage_checker_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente D — Coverage Checker.

    Lee del estado:    claim_id, claim_type, amount_requested.
    Escribe en estado: coverage_result, reasoning_trace, decisions_log.
    """
    claim_id   = state["claim_id"]
    claim_type = state.get("claim_type") or "default"
    amount     = state.get("amount_requested") or 0.0

    logger.info(
        "[Agente D — CoverageChecker] Inicio — expediente %s | tipo: %s | importe: %.2f EUR",
        claim_id, claim_type, amount,
    )

    # ── Comprobacion determinista contra el catalogo de polizas ───────────
    coverage = check_policy.invoke({
        "claim_id":   claim_id,
        "claim_type": claim_type,
        "amount":     amount,
    })

    # ── Razonamiento (LLM opcional con fallback determinista) ────────────
    fallback = (
        f"Agente D: siniestro '{claim_type}' "
        f"{'cubierto' if coverage['covered'] else 'no cubierto'} segun "
        f"seccion {coverage['policy_section']}. "
        f"Importe neto pagable: {coverage['net_payable']:.2f} EUR "
        f"(limite {coverage['max_coverage']} EUR, franquicia {coverage['deductible']} EUR)."
    )

    reasoning = reason(
        system=(
            "Eres el Agente D (Coverage Checker) del sistema Smart-Claims "
            "de Seguros Pepin. Tu rol es verificar la cobertura de la "
            "poliza para el siniestro. Justifica el resultado citando la "
            "seccion aplicable de la poliza. Responde siempre en castellano."
        ),
        prompt=(
            f"Resultado de la verificacion de cobertura:\n"
            f"- Expediente: {claim_id}\n"
            f"- Tipo de siniestro: {claim_type}\n"
            f"- Importe reclamado: {amount} EUR\n"
            f"- Cubierto: {coverage['covered']}\n"
            f"- Limite maximo: {coverage['max_coverage']} EUR\n"
            f"- Franquicia: {coverage['deductible']} EUR\n"
            f"- Neto pagable: {coverage['net_payable']} EUR\n"
            f"- Seccion aplicable: {coverage['policy_section']}\n\n"
            f"Justifica la cobertura citando la seccion de la poliza."
        ),
        fallback=fallback,
    )

    logger.info(
        "[Agente D] Cobertura — covered=%s | net=%.2f EUR",
        coverage["covered"], coverage["net_payable"],
    )

    return {
        "coverage_result": coverage,
        "reasoning_trace": [reasoning],
        "decisions_log":   [{
            "agent":         "agent_d_coverage_checker",
            "action":        "covered" if coverage["covered"] else "not_covered",
            "reasoning":     reasoning,
            "confidence":    None,
            "hitl_required": False,
        }],
    }
