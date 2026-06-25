"""
Análisis multimodal real con Claude Vision (Agente C).

Dado el contenido binario de un documento (imagen o PDF), invoca a Claude con
capacidades de visión y extrae datos estructurados del expediente. Si no hay
clave de API o la llamada falla, devuelve None (el agente C usa entonces su
camino simulado), de modo que la demo nunca se rompe.

NOTA: a diferencia de las integraciones con sistemas de Seguros Pepín (que se
mantienen simuladas), Claude es el LLM del propio proyecto. Por tanto, esta
extracción multimodal es REAL, no un mock.
"""
from __future__ import annotations

import base64
import json
import logging
import os

logger = logging.getLogger(__name__)

# Modelo del proyecto (mismo que el resto del sistema).
MODEL = "claude-sonnet-4-6"

_PROMPT = (
    "Eres un agente de extracción documental de una aseguradora. Analiza el "
    "documento adjunto (factura, foto de daños, acta, informe de taller, etc.) "
    "y devuelve ÚNICAMENTE un objeto JSON válido, sin texto adicional ni "
    "explicaciones, con esta forma exacta:\n"
    '{"doc_type": "<tipo: factura|foto_danos|acta|informe_taller|otro>", '
    '"amount": <importe en euros como número, o null si no aplica>, '
    '"date": "<fecha YYYY-MM-DD o null>", '
    '"vendor": "<emisor/taller/entidad o null>", '
    '"summary": "<resumen breve en castellano de lo que muestra el documento>", '
    '"confidence": <confianza de la extracción entre 0 y 1>}'
)


def _media_block(data: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(data).decode("utf-8")
    if media_type == "application/pdf":
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}}
    return {"type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64}}


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    # Quita vallas de código markdown si Claude las añade.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def analyze_document(data: bytes, media_type: str, filename: str = "") -> dict | None:
    """Extrae datos estructurados de un documento con Claude Vision.

    Returns:
        dict con doc_type, amount, date, vendor, summary, confidence; o None si
        no hay clave de API o la extracción falla.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [_media_block(data, media_type), {"type": "text", "text": _PROMPT}],
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        result = _parse_json(text)
        if result is not None:
            result["filename"] = filename
            result["model"] = MODEL
        return result
    except Exception as exc:  # cualquier error → None (la demo no se rompe)
        logger.warning("Extracción multimodal con Claude falló (%s): %s", filename, exc)
        return None
