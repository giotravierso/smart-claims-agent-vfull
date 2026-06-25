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
import os

from app.agents.reasoning import reason
from app.tools.claim_tools import check_policy

logger = logging.getLogger(__name__)


def _coverage_via_rag(claim_id: str, claim_type: str, amount: float, description: str) -> dict | None:
    """Verificación de cobertura mediante RAG real (ChromaDB) sobre las pólizas.

    Recupera la cláusula más relevante por similitud vectorial y calcula la
    cobertura a partir de la póliza recuperada. None si el RAG no está activo
    o no disponible (el agente cae entonces a la mock tool check_policy).
    """
    if not os.getenv("SCA_RAG_ENABLED"):
        return None
    try:
        from app.rag.policy_store import retrieve_policy
    except Exception:
        return None
    rag = retrieve_policy(claim_type, description)
    if not rag or not rag.get("claim_type"):
        return None
    covered = bool(rag["covered"])
    net = max(0.0, min(amount, rag["max_coverage"]) - rag["deductible"]) if covered else 0.0
    return {
        "claim_id":          claim_id,
        "claim_type":        claim_type,
        "amount_requested":  amount,
        "covered":           covered,
        "max_coverage":      rag["max_coverage"],
        "deductible":        rag["deductible"],
        "net_payable":       net,
        "policy_section":    rag["section"],
        "source":            "rag",
        "retrieval_distance": rag.get("distance"),
        "retrieved_snippet": rag.get("snippet"),
    }


async def coverage_checker_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente D — Coverage Checker.

    Lee del estado:    claim_id, claim_type, amount_requested, extraction_result.
    Escribe en estado: coverage_result, reasoning_trace, decisions_log.

    Si el RAG está activo (SCA_RAG_ENABLED), recupera la póliza relevante de
    ChromaDB; si no, usa la mock tool check_policy (catálogo determinista).
    """
    claim_id   = state["claim_id"]
    claim_type = state.get("claim_type") or "default"
    amount     = state.get("amount_requested") or 0.0

    logger.info(
        "[Agente D — CoverageChecker] Inicio — expediente %s | tipo: %s | importe: %.2f EUR",
        claim_id, claim_type, amount,
    )

    # Enriquecer la consulta RAG con el resumen de lo extraído por el Agente C.
    ex = state.get("extraction_result") or {}
    description = " ".join(
        str(d.get("summary", "")) for d in (ex.get("by_document") or {}).values()
    )[:300]

    # ── Cobertura por RAG real, con fallback determinista (check_policy) ───
    coverage = _coverage_via_rag(claim_id, claim_type, amount, description)
    if coverage is None:
        coverage = check_policy.invoke({
            "claim_id":   claim_id,
            "claim_type": claim_type,
            "amount":     amount,
        })
        coverage["source"] = "mock"

    # ── Razonamiento (LLM opcional con fallback determinista) ────────────
    via = ("recuperada por RAG vectorial sobre las pólizas (ChromaDB)"
           if coverage.get("source") == "rag" else "según el catálogo de pólizas")
    fallback = (
        f"Agente D: cobertura {via}. Siniestro '{claim_type}' "
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
