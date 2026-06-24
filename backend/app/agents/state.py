"""
Estado compartido del grafo de agentes (LangGraph).

ClaimState es la única fuente de verdad durante la ejecución del flujo.
Lo propaga LangGraph automáticamente entre nodos: cada agente lee lo que
necesita y devuelve una actualización parcial que se fusiona con el estado
existente.

Los acumuladores reasoning_trace y decisions_log usan `operator.add`, de
forma que múltiples agentes pueden añadir contribuciones sin pisarse entre
sí. Este patrón es esencial para la trazabilidad del Chain of Thought.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ClaimState(TypedDict, total=False):
    # ── Identidad del expediente ──────────────────────────────────────────
    claim_id:         str
    client_id:        str
    client_email:     str

    # ── Datos de entrada ──────────────────────────────────────────────────
    claim_type:       str
    amount_requested: float
    channel:          str
    documents:        list[str]

    # ── Conversación / ReAct ──────────────────────────────────────────────
    messages: Annotated[list[BaseMessage], add_messages]

    # ── Resultados parciales de cada agente ───────────────────────────────
    validation_result: dict     # Agente B
    fraud_result:      dict     # Agente G
    extraction_result: dict     # Agente C
    coverage_result:   dict     # Agente D
    resolution:        dict     # Agente E

    # ── Acumuladores (cada agente añade su contribución) ──────────────────
    reasoning_trace: Annotated[list[str], operator.add]
    decisions_log:   Annotated[list[dict], operator.add]

    # ── Control de flujo ──────────────────────────────────────────────────
    status:             str
    decision:           str
    hitl_required:      bool
    terminate:          bool
    termination_reason: str
