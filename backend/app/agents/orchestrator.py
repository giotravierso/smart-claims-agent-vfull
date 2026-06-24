"""
Orchestrator — Agente A del sistema Smart-Claims de Seguros Pepin.

Implementa el patron Supervisor (Hub-and-Spoke) sobre LangGraph. El
supervisor es el UNICO componente que decide el flujo: lee el estado
acumulado y enruta al siguiente agente. Los agentes son nodos puros que
hacen su trabajo y devuelven el control al supervisor.

Mapa de agentes (referencia memoria TFM):
    Agente A → orchestrator.py          (este fichero, supervisor)
    Agente B → document_validator.py
    Agente C → multimodal_extractor.py
    Agente D → coverage_checker.py
    Agente E → claim_resolver.py
    Agente G → fraud_compliance.py

La persistencia de decisiones es centralizada: cada agente acumula su
contribucion en decisions_log durante la ejecucion del grafo, y al
finalizar process_claim persiste todo en MariaDB en una unica transaccion.
Si la BD no esta disponible, la persistencia falla silenciosamente y el
flujo devuelve igualmente el resultado (resiliencia para la demo).
"""
from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from app.agents.claim_resolver       import claim_resolver_node
from app.agents.coverage_checker     import coverage_checker_node
from app.agents.document_validator   import document_validator_node
from app.agents.fraud_compliance     import fraud_compliance_node
from app.agents.multimodal_extractor import multimodal_extractor_node
from app.agents.reasoning            import reason
from app.agents.state                import ClaimState
from app.db.models                   import ClaimStatus
from app.db.repository               import log_agent_decision, save_claim

logger = logging.getLogger(__name__)


# ── Nodo de triaje (entrada al grafo) ─────────────────────────────────────

async def triage_node(state: dict) -> dict:
    """
    Agente A — triaje inicial del expediente.

    No decide enrutamiento (de eso se ocupa el supervisor); su rol es
    enriquecer el estado con el razonamiento de bienvenida y dejar el
    expediente listo para el primer agente especialista.
    """
    claim_id = state["claim_id"]
    logger.info("[Agente A — Orchestrator] Triaje iniciado — expediente %s", claim_id)

    fallback = (
        f"Agente A: expediente {claim_id} de tipo '{state.get('claim_type')}' "
        f"por importe {state.get('amount_requested') or 0} EUR. Se inicia el "
        f"flujo de procesamiento con cribado antifraude como filtro de entrada."
    )

    reasoning = reason(
        system=(
            "Eres el Agente A (Orchestrator) del sistema Smart-Claims de "
            "Seguros Pepin. Tu rol es analizar el expediente entrante y "
            "razonar el triaje. Responde siempre en castellano."
        ),
        prompt=(
            f"Reclamacion recibida:\n"
            f"- ID: {state.get('claim_id')}\n"
            f"- Cliente: {state.get('client_id')}\n"
            f"- Tipo: {state.get('claim_type')}\n"
            f"- Importe: {state.get('amount_requested')}\n"
            f"- Canal: {state.get('channel')}\n"
            f"- Documentos aportados: {state.get('documents')}\n\n"
            f"Razona el triaje paso a paso."
        ),
        fallback=fallback,
    )

    return {
        "status":          ClaimStatus.OPEN.value,
        "reasoning_trace": [reasoning],
        "decisions_log":   [{
            "agent":         "agent_a_orchestrator",
            "action":        "triage",
            "reasoning":     reasoning,
            "confidence":    None,
            "hitl_required": False,
        }],
    }


# ── SUPERVISOR — el cerebro del enrutamiento ──────────────────────────────

def supervisor_router(state: dict) -> str:
    """
    Nucleo del patron Hub-and-Spoke.

    Lee el estado acumulado y decide DETERMINISTICAMENTE el proximo agente.
    Ningun agente tiene su propio router: todos retornan aqui.

    Orden de evaluacion:
    1.  Flujo terminado          → END
    2.  Cribado fraude pendiente → fraud_compliance (Agente G)
    3.  Cliente flagged          → END (caso bloqueado)
    4.  Validacion pendiente     → document_validator (Agente B)
    5.  Documentos incompletos   → END (cliente notificado)
    6.  Extraccion pendiente     → multimodal_extractor (Agente C)
    7.  Cobertura pendiente      → coverage_checker (Agente D)
    8.  Resolucion pendiente     → claim_resolver (Agente E)
    9.  Todo completo            → END
    """
    claim_id = state.get("claim_id", "?")

    # 1. Terminacion explicita (rechazo, pago aprobado, HITL activado)
    if state.get("terminate"):
        reason_term = state.get("termination_reason", "completado")
        logger.info("[Supervisor] %s → END (%s)", claim_id, reason_term)
        return END

    # 2-3. Cribado de fraude (filtro de entrada)
    if state.get("fraud_result") is None:
        logger.info("[Supervisor] %s → fraud_compliance", claim_id)
        return "fraud_compliance"

    if state["fraud_result"].get("is_flagged"):
        logger.info("[Supervisor] %s → END (bloqueado por fraude/OFAC)", claim_id)
        return END

    # 4-5. Validacion documental
    if state.get("validation_result") is None:
        logger.info("[Supervisor] %s → document_validator", claim_id)
        return "document_validator"

    if not state["validation_result"].get("is_valid"):
        logger.info("[Supervisor] %s → END (documentacion incompleta)", claim_id)
        return END

    # 6. Extraccion multimodal
    if state.get("extraction_result") is None:
        logger.info("[Supervisor] %s → multimodal_extractor", claim_id)
        return "multimodal_extractor"

    # 7. Verificacion de cobertura
    if state.get("coverage_result") is None:
        logger.info("[Supervisor] %s → coverage_checker", claim_id)
        return "coverage_checker"

    # 8. Resolucion final
    if state.get("resolution") is None:
        logger.info("[Supervisor] %s → claim_resolver", claim_id)
        return "claim_resolver"

    # 9. Nada pendiente
    logger.info("[Supervisor] %s → END (flujo completo)", claim_id)
    return END


# ── Construccion del grafo ────────────────────────────────────────────────

def build_orchestrator():
    graph = StateGraph(ClaimState)

    # Nodos: 1 hub + 5 agentes especialistas
    graph.add_node("triage",               triage_node)
    graph.add_node("fraud_compliance",     fraud_compliance_node)
    graph.add_node("document_validator",   document_validator_node)
    graph.add_node("multimodal_extractor", multimodal_extractor_node)
    graph.add_node("coverage_checker",     coverage_checker_node)
    graph.add_node("claim_resolver",       claim_resolver_node)

    # Entrada
    graph.set_entry_point("triage")

    # Tras triaje: el supervisor decide
    spoke_destinations = {
        "fraud_compliance":     "fraud_compliance",
        "document_validator":   "document_validator",
        "multimodal_extractor": "multimodal_extractor",
        "coverage_checker":     "coverage_checker",
        "claim_resolver":       "claim_resolver",
        END:                    END,
    }
    graph.add_conditional_edges("triage", supervisor_router, spoke_destinations)

    # Cada agente vuelve al supervisor (Hub-and-Spoke)
    for agent in ["fraud_compliance", "document_validator", "multimodal_extractor",
                  "coverage_checker", "claim_resolver"]:
        graph.add_conditional_edges(agent, supervisor_router, spoke_destinations)

    return graph.compile()


orchestrator = build_orchestrator()


# ── Normalizacion del estado final ────────────────────────────────────────

def _normalize_final_state(final: dict) -> dict:
    """
    Garantiza que el estado final tiene un `status` y un `decision`
    coherentes con el resultado del flujo.

    Hay tres casos en los que el flujo se corta sin que un agente actualice
    explicitamente el status (que se quedaria en "open" tras el triaje):

    1. El cribado de fraude marca el caso como flagged.
    2. La validacion documental detecta documentos incompletos.
    3. Cualquier otra ruta que termine en END sin pasar por claim_resolver.

    Esta funcion deduce el status correcto a partir de los resultados
    parciales acumulados en el estado.
    """
    current_status = final.get("status")

    # Si el resolver ya ha establecido un status final, no lo tocamos
    if current_status not in (None, "", ClaimStatus.OPEN.value):
        return final

    # Caso 1: caso bloqueado por fraude
    if final.get("fraud_result", {}).get("is_flagged"):
        final["status"]             = ClaimStatus.REJECTED.value
        final["decision"]           = "RECHAZO_FRAUDE"
        final["termination_reason"] = final.get("termination_reason") or "caso bloqueado por fraude/OFAC"
        return final

    # Caso 2: documentacion incompleta
    validation = final.get("validation_result") or {}
    if validation and not validation.get("is_valid"):
        final["status"]             = ClaimStatus.VALIDATING.value
        final["decision"]           = "INFO_REQUERIDA"
        final["termination_reason"] = (
            final.get("termination_reason")
            or f"documentacion incompleta: faltan {', '.join(validation.get('missing_docs', []))}"
        )
        return final

    # Caso 3: el resolver ya habra escrito su status; si no, queda en open
    return final


# ── API publica ───────────────────────────────────────────────────────────

async def process_claim(
    claim_id:         str,
    client_id:        str,
    claim_type:       str,
    amount_requested: float | None    = None,
    channel:          str             = "email",
    documents:        list[str] | None = None,
    client_email:     str             = "cliente@example.com",
) -> dict:
    """
    Procesa un expediente a traves del grafo de agentes y persiste las
    decisiones en MariaDB.

    La persistencia esta envuelta en try/except: si no hay base de datos
    disponible (p. ej. la CLI de demo sin MariaDB), el flujo devuelve
    igualmente su resultado. Es una propiedad clave de resiliencia para
    la demostracion ante tribunal.
    """
    initial: ClaimState = {
        "claim_id":         claim_id,
        "client_id":        client_id,
        "client_email":     client_email,
        "claim_type":       claim_type,
        "amount_requested": amount_requested,
        "channel":          channel,
        "documents":        documents or [],
        "reasoning_trace":  [],
        "decisions_log":    [],
    }

    final = await orchestrator.ainvoke(initial)

    # Normaliza status y decision cuando el flujo se ha cortado sin pasar
    # por el claim_resolver (fraude detectado, documentos incompletos, etc.)
    final = _normalize_final_state(final)

    # Persistencia best-effort: si falla, la demo no se rompe
    try:
        await save_claim(
            claim_id         = claim_id,
            client_id        = client_id,
            claim_type       = claim_type,
            channel          = channel,
            amount_requested = amount_requested,
            amount_approved  = (final.get("resolution") or {}).get("amount_paid"),
            status           = ClaimStatus(final.get("status", ClaimStatus.OPEN.value)),
        )
        for d in final.get("decisions_log", []):
            await log_agent_decision(
                claim_id      = claim_id,
                agent         = d["agent"],
                action        = d["action"],
                reasoning     = d["reasoning"],
                confidence    = d.get("confidence"),
                hitl_required = d.get("hitl_required", False),
            )
    except Exception as exc:
        logger.warning("No se han podido persistir las decisiones de %s: %s",
                       claim_id, exc)

    return final
