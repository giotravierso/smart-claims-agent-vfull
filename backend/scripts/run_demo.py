"""
CLI de demostració del sistema Smart-Claims.

Executa el flux d'agents sobre casos representatius i mostra el raonament
(Chain of Thought) i la decisió final de cada expedient. No requereix base
de dades (la persistència és best-effort dins de process_claim).

Ús (des de backend/):  py scripts/run_demo.py
"""
import asyncio
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import process_claim  # noqa: E402

# Llavor fixa perquè la demostració sigui REPRODUÏBLE (el mock check_fraud usa
# random). Així cada cas mostra sempre el mateix camí davant del tribunal.
random.seed(20)

FULL_DOCS = ["foto_danys", "factura", "acta_policial"]

CASES = [
    {"claim_id": "DEMO-PAGO", "client_id": "C-A", "claim_type": "danys_propis",
     "amount_requested": 3200.0, "channel": "email", "doc_types": FULL_DOCS},
    {"claim_id": "DEMO-HITL", "client_id": "C-B", "claim_type": "responsabilitat",
     "amount_requested": 8500.0, "channel": "web", "doc_types": FULL_DOCS},
    {"claim_id": "DEMO-RECHAZO", "client_id": "C-C", "claim_type": "danys_mecànics",
     "amount_requested": 1000.0, "channel": "email", "doc_types": FULL_DOCS},
    {"claim_id": "DEMO-INFO", "client_id": "C-D", "claim_type": "danys_propis",
     "amount_requested": 1000.0, "channel": "email", "doc_types": ["factura"]},
]


async def main() -> None:
    for case in CASES:
        print("=" * 70)
        print(f"EXPEDIENT: {case['claim_id']}  ({case['claim_type']}, "
              f"{case['amount_requested']}€)")
        print("-" * 70)
        result = await process_claim(**case)
        print("Raonament (Chain of Thought):")
        for i, step in enumerate(result.get("reasoning_trace", []), 1):
            print(f"  {i}. {step}")
        print(f"\n>>> DECISIÓ: {result.get('decision')}   "
              f"(HITL: {result.get('hitl_required')})")
        print()


if __name__ == "__main__":
    asyncio.run(main())
