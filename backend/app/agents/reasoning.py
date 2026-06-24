"""
Helper de razonamiento — LLM opcional con fallback determinista.

Si la variable de entorno ANTHROPIC_API_KEY está disponible, genera el
razonamiento (Chain of Thought) invocando a Claude. Si no está disponible
o la llamada falla, devuelve el `fallback` determinista que pasa quien
invoca.

Esta dualidad es una decisión de diseño deliberada: garantiza que la
demostración funcione siempre (con o sin conectividad, con o sin clave de
API válida) y reduce drásticamente el coste de los tests, que no necesitan
mock de la red.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


def reason(system: str, prompt: str, fallback: str) -> str:
    """
    Devuelve un razonamiento en lenguaje natural.

    Args:
        system:   Instrucción de sistema que define el rol del agente.
        prompt:   Contexto concreto del expediente que se está procesando.
        fallback: Texto determinista que se devuelve si el LLM no está
                  disponible o la llamada falla.

    Returns:
        El razonamiento generado por Claude, o el `fallback` si no hay
        clave de API o se produce cualquier error en la llamada.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        return fallback

    try:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model=MODEL, max_tokens=1024, temperature=0)
        response = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ])
        content = response.content
        return content if isinstance(content, str) else str(content)

    except Exception as exc:
        # Cualquier error (red, cuota, autenticación) → fallback.
        # La demo nunca se rompe por un fallo del LLM externo.
        logger.warning("Fallback de razonamiento (LLM no disponible): %s", exc)
        return fallback
