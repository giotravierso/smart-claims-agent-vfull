"""
Agents especialistes (treballadors) del sistema Smart-Claims.

Cada agent és un node pur de LangGraph: invoca la seva mock tool, raona i
registra la seva decisió a l'estat. NO escriu a la base de dades (la persistència
es centralitza a process_claim). Així es poden provar sense BD.
"""
from __future__ import annotations

from app.agents.reasoning import reason
from app.tools.claim_tools import (
    validate_documents,
    extract_multimodal,
    check_policy,
    check_fraud,
)

REQUIRED_DOCS = ["foto_danys", "factura", "acta_policial"]


async def agent_b_validate(state: dict) -> dict:
    """Agent B — Validació documental (completesa i vigència del contracte).

    🔌 MOCK → API: en producció validaria els adjunts contra el gestor
    documental real de Seguros Pepín i el sistema de pòlisses vigents.
    """
    result = validate_documents.invoke({
        "claim_id": state["claim_id"],
        "doc_types": state.get("doc_types", []),
    })
    fallback = (
        f"Agent B: documentació {'completa i vàlida' if result['is_valid'] else 'incompleta'}; "
        f"manquen {result['missing_docs'] or 'cap document'}."
    )
    reasoning = reason(
        system="Ets l'Agent B, especialista en validació documental.",
        prompt=f"Resultat de la validació documental: {result}",
        fallback=fallback,
    )
    return {
        "validation": result,
        "reasoning_trace": [reasoning],
        "decisions_log": [{
            "agent": "agent_b",
            "action": "validate_documents",
            "reasoning": reasoning,
            "confidence": None,
            "hitl_required": False,
        }],
    }


async def agent_c_extract(state: dict) -> dict:
    """Agent C — Extracció multimodal (lectura de factures i adjunts via VLM).

    🔌 MOCK → API: en producció executaria Claude Vision real sobre els
    adjunts de l'expedient (factures, fotos de danys, actes).
    """
    result = extract_multimodal.invoke({
        "claim_id": state["claim_id"],
        "file_url": f"mock://{state['claim_id']}/factura.pdf",
        "doc_type": "factura",
    })
    fallback = (
        f"Agent C: dades extretes {result['extracted']} "
        f"amb confiança {result['confidence']:.2f}."
    )
    reasoning = reason(
        system="Ets l'Agent C, especialista en extracció multimodal de documents.",
        prompt=f"Resultat de l'extracció multimodal: {result}",
        fallback=fallback,
    )
    return {
        "extraction": result,
        "reasoning_trace": [reasoning],
        "decisions_log": [{
            "agent": "agent_c",
            "action": "extract_multimodal",
            "reasoning": reasoning,
            "confidence": result["confidence"],
            "hitl_required": False,
        }],
    }


async def agent_d_policy(state: dict) -> dict:
    """Agent D — Verificació de pòlissa (cobertura, límits i franquícia).

    🔌 MOCK → API: en producció faria recuperació RAG sobre les pòlisses
    reals indexades a ChromaDB (fase posterior).
    """
    result = check_policy.invoke({
        "claim_id": state["claim_id"],
        "claim_type": state["claim_type"],
        "amount": state.get("amount_requested") or 0.0,
    })
    fallback = (
        f"Agent D: sinistre '{result['claim_type']}' "
        f"{'cobert' if result['covered'] else 'no cobert'}; "
        f"import net pagable {result['net_payable']}€ "
        f"(secció {result['policy_section']})."
    )
    reasoning = reason(
        system="Ets l'Agent D, especialista en verificació de pòlisses.",
        prompt=f"Resultat de la verificació de pòlissa: {result}",
        fallback=fallback,
    )
    return {
        "policy_check": result,
        "reasoning_trace": [reasoning],
        "decisions_log": [{
            "agent": "agent_d",
            "action": "check_policy",
            "reasoning": reasoning,
            "confidence": None,
            "hitl_required": False,
        }],
    }


async def agent_g_fraud(state: dict) -> dict:
    """Agent G — Frau i compliment (filtre primerenc OFAC/LA-FT).

    🔌 MOCK → API: en producció consultaria les llistes OFAC/ONU i el motor
    antifrau corporatiu de Seguros Pepín amb el client_id real (anonimitzat).
    """
    result = check_fraud.invoke({
        "claim_id": state["claim_id"],
        "client_id": state.get("client_id", "desconegut"),
        "amount": state.get("amount_requested") or 0.0,
    })
    fallback = (
        f"Agent G: risc de frau {result['risk_score']:.2f}; "
        f"{'MARCAT per a revisió' if result['is_flagged'] else 'sense indicis rellevants'}."
    )
    reasoning = reason(
        system="Ets l'Agent G, especialista en frau i compliment.",
        prompt=f"Resultat del cribratge antifrau: {result}",
        fallback=fallback,
    )
    return {
        "fraud_check": result,
        "reasoning_trace": [reasoning],
        "decisions_log": [{
            "agent": "agent_g",
            "action": "check_fraud",
            "reasoning": reasoning,
            "confidence": None,
            "hitl_required": result["is_flagged"],
        }],
    }
