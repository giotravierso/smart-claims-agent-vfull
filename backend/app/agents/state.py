"""Estat compartit del graf d'agents (LangGraph)."""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ClaimState(TypedDict, total=False):
    # Dades d'entrada de l'expedient
    claim_id: str
    client_id: str
    claim_type: str
    amount_requested: float
    channel: str
    doc_types: list[str]

    # Conversa / ReAct
    messages: Annotated[list[BaseMessage], add_messages]

    # Resultats parcials de cada agent
    validation: dict
    extraction: dict
    policy_check: dict
    fraud_check: dict

    # Traça i acumuladors
    reasoning_trace: Annotated[list[str], operator.add]
    decisions_log: Annotated[list[dict], operator.add]

    # Resolució
    status: str
    decision: str
    hitl_required: bool
