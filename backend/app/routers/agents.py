"""
Endpoint informativo sobre los agentes del sistema.
"""
from fastapi import APIRouter

router = APIRouter()


AGENTS_INFO = [
    {
        "id":             "A",
        "name":           "Orchestrator",
        "file":           "orchestrator.py",
        "responsibility": "Triaje, enrutamiento y control del estado del expediente",
        "status":         "operational",
    },
    {
        "id":             "B",
        "name":           "Document Validator",
        "file":           "document_validator.py",
        "responsibility": "Validacion documental contra los requisitos del tipo de siniestro",
        "status":         "operational",
    },
    {
        "id":             "C",
        "name":           "Multimodal Extractor",
        "file":           "multimodal_extractor.py",
        "responsibility": "Extraccion de datos de facturas, fotos y actas via VLM",
        "status":         "operational",
    },
    {
        "id":             "D",
        "name":           "Coverage Checker",
        "file":           "coverage_checker.py",
        "responsibility": "Verificacion de cobertura segun el catalogo de polizas",
        "status":         "operational",
    },
    {
        "id":             "E",
        "name":           "Claim Resolver",
        "file":           "claim_resolver.py",
        "responsibility": "Decision final y ejecucion (pago, rechazo o HITL)",
        "status":         "operational",
    },
    {
        "id":             "G",
        "name":           "Fraud Compliance",
        "file":           "fraud_compliance.py",
        "responsibility": "Cribado OFAC y score de fraude como filtro de entrada",
        "status":         "operational",
    },
]


@router.get("/status")
async def agents_status() -> dict:
    """Devuelve el estado y descripcion de los agentes del sistema."""
    return {
        "pattern":      "Supervisor (Hub-and-Spoke) sobre LangGraph",
        "agent_count":  len(AGENTS_INFO),
        "agents":       AGENTS_INFO,
    }
