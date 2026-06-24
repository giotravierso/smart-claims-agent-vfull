"""
Multimodal Extractor — Agente C del sistema Smart-Claims de Seguros Pepin.

Responsabilidad unica: extraer datos estructurados de los documentos
adjuntos (facturas, fotos de danos, actas policiales) usando un modelo
con capacidades de vision (VLM).

Si la confianza de extraccion es baja, marca el documento para revision
manual. En producccion haria fallback a OCR clasico (Tesseract).

Referencia en la memoria del TFM: Agente C (multimodal_extractor.py).
"""
from __future__ import annotations

import logging

from app.agents.reasoning import reason
from app.tools.claim_tools import extract_multimodal

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.85


async def multimodal_extractor_node(state: dict) -> dict:
    """
    Nodo LangGraph del Agente C — Multimodal Extractor.

    Lee del estado: claim_id, documents.
    Escribe en el estado: extraction_result, reasoning_trace, decisions_log.
    """
    claim_id  = state["claim_id"]
    documents = state.get("documents") or []

    logger.info(
        "[Agente C — MultimodalExtractor] Inicio — expediente %s | docs: %s",
        claim_id, documents,
    )

    # ── Extraccion determinista por cada documento ────────────────────────
    extracted: dict[str, dict] = {}
    low_confidence_docs: list[str] = []
    inferred_amount = 0.0

    for doc_type in documents:
        result = extract_multimodal.invoke({
            "claim_id": claim_id,
            "file_url": f"mock://{claim_id}/{doc_type}.bin",
            "doc_type": doc_type,
        })
        extracted[doc_type] = result

        if result["confidence"] < LOW_CONFIDENCE_THRESHOLD:
            low_confidence_docs.append(doc_type)

        # Infiere el importe maximo del expediente si aparece en algun documento
        amount = result.get("extracted", {}).get("amount")
        if isinstance(amount, (int, float)):
            inferred_amount = max(inferred_amount, float(amount))

    avg_confidence = (
        round(sum(d["confidence"] for d in extracted.values()) / len(extracted), 3)
        if extracted else 0.0
    )

    extraction_result = {
        "claim_id":            claim_id,
        "by_document":         extracted,
        "low_confidence_docs": low_confidence_docs,
        "inferred_amount":     inferred_amount,
        "avg_confidence":      avg_confidence,
    }

    # ── Razonamiento (LLM opcional con fallback determinista) ────────────
    fallback = (
        f"Agente C: extraidos {len(extracted)} documentos con confianza media "
        f"{avg_confidence:.2f}. "
        f"{f'Atencion: baja confianza en {low_confidence_docs}.' if low_confidence_docs else 'Todas las extracciones por encima del umbral.'} "
        f"Importe inferido: {inferred_amount:.2f} EUR."
    )

    reasoning = reason(
        system=(
            "Eres el Agente C (Multimodal Extractor) del sistema Smart-Claims "
            "de Seguros Pepin. Tu rol es extraer datos estructurados de los "
            "documentos del expediente. Justifica el resultado con detalle "
            "tecnico. Responde siempre en castellano."
        ),
        prompt=(
            f"Resultado de la extraccion multimodal:\n"
            f"- Expediente: {claim_id}\n"
            f"- Documentos procesados: {list(extracted.keys())}\n"
            f"- Confianza media: {avg_confidence}\n"
            f"- Documentos con baja confianza: {low_confidence_docs}\n"
            f"- Importe inferido: {inferred_amount} EUR\n\n"
            f"Resume los hallazgos clave para los siguientes agentes."
        ),
        fallback=fallback,
    )

    logger.info(
        "[Agente C] Extraccion completada — %d docs | confianza media %.3f | importe inferido %.2f EUR",
        len(extracted), avg_confidence, inferred_amount,
    )

    update = {
        "extraction_result": extraction_result,
        "reasoning_trace":   [reasoning],
        "decisions_log":     [{
            "agent":         "agent_c_multimodal_extractor",
            "action":        "extracted",
            "reasoning":     reasoning,
            "confidence":    avg_confidence,
            "hitl_required": False,
        }],
    }

    # Si el state no traia importe declarado, usar el inferido
    if not state.get("amount_requested") and inferred_amount > 0:
        update["amount_requested"] = inferred_amount

    return update
