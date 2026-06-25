"""
Evaluador in-process del sistema Smart-Claims sobre dataset sintético.

A diferencia de evaluate_dataset.py (que requiere el backend REST levantado en
Docker), este evaluador invoca `process_claim` EN PROCESO — no necesita servidor
ni MariaDB. Está alineado con el vocabulario de decisiones ACTUAL
(PAGO / RECHAZO / REVISION_HUMANA / INFO_REQUERIDA / RECHAZO_FRAUDE) y refleja
el sistema real: motor antifraude de 4 detectores, RAG de pólizas y resolución.

Incluye casos OFAC (nombre sancionado) para demostrar el detector real.

Uso (desde backend/):  py scripts/evaluate_inprocess.py
"""
from __future__ import annotations

import asyncio
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.pop("ANTHROPIC_API_KEY", None)      # razonamiento determinista (reproducible)
os.environ.setdefault("SCA_RAG_ENABLED", "1")  # Agente D con RAG real

from app.agents.orchestrator import process_claim  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DOCS = {
    "danys_propis":    ["foto_danys", "factura", "denuncia_companyia"],
    "responsabilitat": ["foto_danys", "acta_policial", "dades_tercer"],
    "robatori":        ["acta_policial", "llista_objectes_robats"],
    "danys_mecanics":  ["informe_taller", "factura"],
}

# Decisiones aceptables por escenario (vocabulario ACTUAL)
EXPECTED = {
    "pago_automatico":      {"PAGO"},
    "hitl":                 {"REVISION_HUMANA"},
    "rechazo_no_cobertura": {"RECHAZO"},
    "info_incompleta":      {"INFO_REQUERIDA"},
    "fraude_ofac":          {"RECHAZO_FRAUDE"},
    "potencial_fraude":     {"REVISION_HUMANA", "RECHAZO_FRAUDE", "RECHAZO"},  # cualquier no-PAGO
}


def build_cases() -> list[dict]:
    cases: list[dict] = []
    i = 1

    def add(claim_type, amount, scenario, complete=True, drop=None, client_name="Maria Garcia"):
        nonlocal i
        docs = list(DOCS[claim_type])
        if not complete and drop:
            docs = [d for d in docs if d != drop]
        cases.append({
            "claim_id": f"CLM-DATASET-{i:03d}", "client_id": f"CLIENT-{i:03d}",
            "client_name": client_name, "claim_type": claim_type,
            "amount_requested": float(amount), "documents": docs, "scenario": scenario,
        })
        i += 1

    # Bloque 1 — Pago automático (10)
    for ct, amt in [("danys_propis",1500),("danys_propis",2300),("danys_propis",3800),
                    ("danys_propis",4500),("responsabilitat",1200),("responsabilitat",2800),
                    ("responsabilitat",4900),("robatori",1800),("robatori",3500),("robatori",4700)]:
        add(ct, amt, "pago_automatico")
    # Bloque 2 — HITL por importe (6)
    for ct, amt in [("danys_propis",7500),("danys_propis",9200),("responsabilitat",15000),
                    ("responsabilitat",25000),("responsabilitat",40000),("robatori",6500)]:
        add(ct, amt, "hitl")
    # Bloque 3 — Rechazo por no cobertura (4)
    for ct, amt in [("danys_mecanics",800),("danys_mecanics",2200),
                    ("danys_mecanics",3500),("danys_mecanics",1500)]:
        add(ct, amt, "rechazo_no_cobertura")
    # Bloque 4 — Información incompleta (8)
    for ct, amt, drop in [("danys_propis",2500,"factura"),("danys_propis",3000,"denuncia_companyia"),
                          ("danys_propis",1800,"foto_danys"),("responsabilitat",4500,"dades_tercer"),
                          ("responsabilitat",6800,"acta_policial"),("robatori",2200,"llista_objectes_robats"),
                          ("robatori",3300,"acta_policial"),("danys_propis",2800,"factura")]:
        add(ct, amt, "info_incompleta", complete=False, drop=drop)
    # Bloque 5 — Fraude OFAC (2): nombre sancionado -> BLOCKED
    add("danys_propis", 3000, "fraude_ofac", client_name="Viktor Nikolaev Kozlov")
    add("robatori", 2500, "fraude_ofac", client_name="Dmitri Volkov")
    # Bloque 6 — Potencial fraude por importe inusual (2)
    add("danys_propis", 9999.99, "potencial_fraude", client_name="Cliente Sospechoso")
    add("robatori", 7777.77, "potencial_fraude", client_name="Cliente Sospechoso")
    return cases


async def run() -> None:
    cases = build_cases()
    records = []
    print(f"Evaluando {len(cases)} casos in-process (RAG activo, sin LLM externo)...\n")
    for c in cases:
        t0 = time.time()
        res = await process_claim(
            claim_id=c["claim_id"], client_id=c["client_id"], claim_type=c["claim_type"],
            amount_requested=c["amount_requested"], channel="web",
            documents=c["documents"], client_name=c["client_name"],
        )
        elapsed = round(time.time() - t0, 3)
        decision = res.get("decision")
        status = res.get("status")
        ok = decision in EXPECTED[c["scenario"]]
        records.append({"claim_id": c["claim_id"], "scenario": c["scenario"],
                        "claim_type": c["claim_type"], "amount": c["amount_requested"],
                        "decision": decision, "status": status,
                        "fraud_verdict": (res.get("fraud_result") or {}).get("verdict"),
                        "coverage_source": (res.get("coverage_result") or {}).get("source"),
                        "correct": ok, "elapsed": elapsed})
        print(f"  {c['claim_id']} {c['scenario']:20s} -> {str(decision):16s} "
              f"[{'OK' if ok else 'X'}]  fraude={records[-1]['fraud_verdict']}")

    n = len(records)
    n_ok = sum(r["correct"] for r in records)
    by_sc = defaultdict(lambda: [0, 0])
    for r in records:
        by_sc[r["scenario"]][1] += 1
        if r["correct"]:
            by_sc[r["scenario"]][0] += 1
    n_hitl = sum(1 for r in records if r["status"] == "pending_review")
    n_auto = sum(1 for r in records if r["status"] in ("resolved", "rejected"))
    confusion = Counter((r["scenario"], r["decision"]) for r in records)

    agg = {
        "n_total": n, "n_correct": n_ok, "accuracy": round(n_ok / n, 3),
        "tra_autonomia": round(n_auto / n, 3), "hitl_rate": round(n_hitl / n, 3),
        "rag_real_rate": round(sum(1 for r in records if r["coverage_source"] == "rag") / n, 3),
        "by_scenario": {s: {"correct": v[0], "total": v[1], "acc": round(v[0]/v[1], 3)}
                        for s, v in by_sc.items()},
        "elapsed_mean": round(statistics.mean(r["elapsed"] for r in records), 3),
        "confusion": {f"{s} -> {d}": c for (s, d), c in confusion.items()},
    }
    (OUT_DIR / "evaluation_inprocess.json").write_text(
        json.dumps({"aggregates": agg, "records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"  Precisión global: {agg['accuracy']:.1%}  ({n_ok}/{n})")
    print(f"  TRA (autonomía):  {agg['tra_autonomia']:.1%}   |  Tasa HITL: {agg['hitl_rate']:.1%}")
    print(f"  Cobertura por RAG real: {agg['rag_real_rate']:.1%}")
    print("  Por escenario:")
    for s, v in agg["by_scenario"].items():
        print(f"    {s:22s} {v['correct']:2d}/{v['total']:2d}  ({v['acc']:.0%})")
    print(f"  Tiempo medio/caso: {agg['elapsed_mean']}s")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run())
