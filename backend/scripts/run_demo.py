"""
CLI de demostracion del sistema Smart-Claims.

Ejecuta el flujo de agentes sobre 4 casos representativos y muestra el
razonamiento (Chain of Thought) y la decision final de cada expediente.
No requiere base de datos: la persistencia es best-effort dentro de
process_claim.

Uso (desde backend/):
    python scripts/run_demo.py
"""
import asyncio
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import process_claim  # noqa: E402


# Semilla fija para que la demostracion sea REPRODUCIBLE
# (el mock de check_fraud usa random).
random.seed(7)


FULL_DOCS_PROPIS  = ["foto_danys", "factura", "denuncia_companyia"]
FULL_DOCS_RESP    = ["foto_danys", "acta_policial", "dades_tercer"]
FULL_DOCS_MECAN   = ["informe_taller", "factura"]


CASES = [
    {
        "claim_id":         "DEMO-PAGO",
        "client_id":        "C-A",
        "claim_type":       "danys_propis",
        "amount_requested": 3200.0,
        "channel":          "email",
        "documents":        FULL_DOCS_PROPIS,
        "scenario":         "Pago automatico (cobertura + importe bajo)",
    },
    {
        "claim_id":         "DEMO-HITL",
        "client_id":        "C-B",
        "claim_type":       "responsabilitat",
        "amount_requested": 8500.0,
        "channel":          "web",
        "documents":        FULL_DOCS_RESP,
        "scenario":         "Revision humana (importe > umbral HITL)",
    },
    {
        "claim_id":         "DEMO-RECHAZO",
        "client_id":        "C-C",
        "claim_type":       "danys_mecanics",
        "amount_requested": 1000.0,
        "channel":          "email",
        "documents":        FULL_DOCS_MECAN,
        "scenario":         "Rechazo por no cobertura",
    },
    {
        "claim_id":         "DEMO-INFO",
        "client_id":        "C-D",
        "claim_type":       "danys_propis",
        "amount_requested": 1000.0,
        "channel":          "email",
        "documents":        ["factura"],   # faltan dos documentos
        "scenario":         "Solicitud de informacion (docs incompletos)",
    },
]


async def main() -> None:
    print()
    print("=" * 78)
    print("  Smart-Claims Agent  —  Demostracion CLI")
    print("=" * 78)

    for case in CASES:
        scenario = case.pop("scenario")
        print()
        print("-" * 78)
        print(f"  Expediente: {case['claim_id']}")
        print(f"  Escenario:  {scenario}")
        print(f"  Tipo:       {case['claim_type']}  |  Importe: {case['amount_requested']} EUR")
        print("-" * 78)

        result = await process_claim(**case)

        print()
        print("  Razonamiento (Chain of Thought):")
        for i, step in enumerate(result.get("reasoning_trace", []), 1):
            # Limita cada paso a 200 caracteres para legibilidad
            preview = step[:200].replace("\n", " ")
            if len(step) > 200:
                preview += " ..."
            print(f"    {i}. {preview}")

        print()
        print(f"  >>> Decision:  {result.get('decision', '-')}")
        print(f"      Estado:    {result.get('status', '-')}")
        print(f"      HITL:      {result.get('hitl_required', False)}")
        amount_paid = (result.get("resolution") or {}).get("amount_paid")
        if amount_paid is not None:
            print(f"      Importe pagado: {amount_paid} EUR")

    print()
    print("=" * 78)
    print("  Demostracion finalizada.")
    print("=" * 78)
    print()


if __name__ == "__main__":
    asyncio.run(main())
