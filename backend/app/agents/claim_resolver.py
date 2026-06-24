"""
Claim Resolver — Agente E del sistema Smart-Claims de Seguros Pepin.

Responsabilidad unica: tomar la decision final basandose en los outputs
de los agentes anteriores y ejecutarla a traves de las Mock APIs.

Reglas de decision deterministas:
- No cubierto                       -> RECHAZO justificado (send_rejection)
- Cubierto + importe <= umbral HITL -> PAGO automatico (approve_payment)
- Cubierto + importe >  umbral HITL -> activa HITL (no se ejecuta pago)

El umbral HITL se configura via la variable HITL_AMOUNT_THRESHOLD
(por defecto 5000 EUR).

Referencia en la memoria del TFM: Agente E (claim_resolver.py).
"""
from __future__ import annotations

import logging
import os

from app.agents.reasoning import reason
from app.tools.claim_tools import approve_payment, send_rejection

logger = logging.getLogger(__name__)

DEFAULT_HITL_THRESHOLD = 5000.0
MOCK_IBAN = "ES7621000418401234567891"


def _hitl_threshold() -> float:
    return float(os.getenv("HITL_AMOUNT_THRESHOLD", DEFAULT_HITL_THRESHOLD))


async def claim_resolver_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente E — Claim Resolver.

    Lee del estado: claim_id, client_email, amount_requested, coverage_result.
    Escribe en el estado: resolution, status, decision, hitl_required,
    terminate, reasoning_trace, decisions_log.
    """
    claim_id     = state["claim_id"]
    client_email = state.get("client_email", "cliente@example.com")
    amount       = state.get("amount_requested") or 0.0
    coverage     = state.get("coverage_result") or {}

    is_covered  = coverage.get("covered", False)
    net_payable = coverage.get("net_payable", 0.0)
    section     = coverage.get("policy_section", "poliza estandar")
    threshold   = _hitl_threshold()

    logger.info(
        "[Agente E — ClaimResolver] Inicio — expediente %s | covered=%s | net=%.2f EUR | umbral=%.2f",
        claim_id, is_covered, net_payable, threshold,
    )

    # ── Caso 1: NO CUBIERTO -> rechazo justificado ───────────────────────
    if not is_covered:
        fallback = (
            f"Agente E: el siniestro no esta cubierto segun la seccion {section} "
            f"de la poliza. Se procede al RECHAZO justificado y se notifica al cliente."
        )
        reasoning = reason(
            system=(
                "Eres el Agente E (Claim Resolver) del sistema Smart-Claims "
                "de Seguros Pepin. Tu rol es la resolucion final del expediente. "
                "Justifica el rechazo con tono profesional y empatico, citando "
                "la seccion de la poliza. Responde siempre en castellano."
            ),
            prompt=(
                f"Resolucion: RECHAZO\n"
                f"- Expediente: {claim_id}\n"
                f"- Seccion aplicable: {section}\n\n"
                f"Redacta la justificacion del rechazo para el cliente."
            ),
            fallback=fallback,
        )

        send_rejection.invoke({
            "claim_id":     claim_id,
            "reason":       reasoning,
            "client_email": client_email,
        })

        return {
            "resolution": {
                "decision":    "rejected",
                "reason":      reasoning,
                "amount_paid": 0.0,
            },
            "status":             "rejected",
            "decision":           "RECHAZO",
            "hitl_required":      False,
            "terminate":          True,
            "termination_reason": "rechazado por no cobertura",
            "reasoning_trace":    [reasoning],
            "decisions_log":      [{
                "agent":         "agent_e_claim_resolver",
                "action":        "send_rejection",
                "reasoning":     reasoning,
                "confidence":    None,
                "hitl_required": False,
            }],
        }

    # ── Caso 2: CUBIERTO + importe alto -> HITL ──────────────────────────
    if net_payable > threshold:
        fallback = (
            f"Agente E: el importe neto pagable ({net_payable:.2f} EUR) supera "
            f"el umbral HITL ({threshold:.2f} EUR). El expediente se deriva "
            f"a REVISION HUMANA antes de autorizar el pago."
        )
        reasoning = reason(
            system=(
                "Eres el Agente E (Claim Resolver) del sistema Smart-Claims "
                "de Seguros Pepin. Justifica la derivacion a revision humana "
                "para un importe alto. Responde siempre en castellano."
            ),
            prompt=(
                f"Resolucion: REVISION HUMANA por importe\n"
                f"- Expediente: {claim_id}\n"
                f"- Importe a pagar: {net_payable} EUR\n"
                f"- Umbral HITL: {threshold} EUR\n\n"
                f"Justifica la derivacion."
            ),
            fallback=fallback,
        )

        return {
            "resolution": {
                "decision":    "pending_review",
                "reason":      reasoning,
                "amount_paid": None,
            },
            "status":             "pending_review",
            "decision":           "REVISION_HUMANA",
            "hitl_required":      True,
            "terminate":          True,
            "termination_reason": f"importe {net_payable} EUR supera umbral HITL ({threshold} EUR)",
            "reasoning_trace":    [reasoning],
            "decisions_log":      [{
                "agent":         "agent_e_claim_resolver",
                "action":        "route_hitl_amount",
                "reasoning":     reasoning,
                "confidence":    None,
                "hitl_required": True,
            }],
        }

    # ── Caso 3: CUBIERTO + importe bajo -> pago automatico ───────────────
    fallback = (
        f"Agente E: cobertura confirmada (seccion {section}) e importe "
        f"{net_payable:.2f} EUR dentro del umbral. Se aprueba el PAGO automatico."
    )
    reasoning = reason(
        system=(
            "Eres el Agente E (Claim Resolver) del sistema Smart-Claims de "
            "Seguros Pepin. Justifica la aprobacion del pago automatico, "
            "citando la seccion de la poliza. Responde siempre en castellano."
        ),
        prompt=(
            f"Resolucion: PAGO automatico\n"
            f"- Expediente: {claim_id}\n"
            f"- Importe neto: {net_payable} EUR\n"
            f"- Umbral HITL: {threshold} EUR\n"
            f"- Seccion aplicable: {section}\n\n"
            f"Redacta la justificacion del pago."
        ),
        fallback=fallback,
    )

    payment_result = approve_payment.invoke({
        "claim_id": claim_id,
        "amount":   net_payable,
        "iban":     MOCK_IBAN,
    })

    logger.info("[Agente E] PAGO APROBADO — %.2f EUR", net_payable)

    return {
        "resolution": {
            "decision":    "approved",
            "reason":      reasoning,
            "amount_paid": net_payable,
            "payment":     payment_result,
        },
        "status":             "resolved",
        "decision":           "PAGO",
        "hitl_required":      False,
        "terminate":          True,
        "termination_reason": "pago aprobado",
        "reasoning_trace":    [reasoning],
        "decisions_log":      [{
            "agent":         "agent_e_claim_resolver",
            "action":        "approve_payment",
            "reasoning":     reasoning,
            "confidence":    None,
            "hitl_required": False,
        }],
    }
