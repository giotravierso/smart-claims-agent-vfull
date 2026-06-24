"""
Generador de dataset sintetico de siniestros para Smart-Claims Agent.

Genera 30 reclamaciones variadas cubriendo los escenarios principales:
- Pago automatico (cobertura + importe bajo + docs completos)
- Revision humana HITL (cobertura + importe alto + docs completos)
- Rechazo por no cobertura (tipo no cubierto)
- Solicitud de informacion (docs incompletos)
- Casos de fraude (importes inusuales, clientes flagged)

El dataset se guarda como JSON en data/synthetic/claims_dataset.json.
Tambien genera un CSV resumen para inspeccion rapida.

Uso:
    docker exec -it sca-backend python scripts/generate_dataset.py
"""
from __future__ import annotations

import csv
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path


random.seed(7)(7)  # reproducibilidad

OUTPUT_DIR = Path("/app/data/synthetic")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLAIM_TYPES = {
    "danys_propis":    ["foto_danys", "factura", "denuncia_companyia"],
    "responsabilitat": ["foto_danys", "acta_policial", "dades_tercer"],
    "robatori":        ["acta_policial", "llista_objectes_robats"],
    "danys_mecanics":  ["informe_taller", "factura"],
}

CHANNELS = ["email", "web", "whatsapp"]

CLIENT_POOL = [
    {"id": "CLIENT-001", "name": "Maria Garcia",    "email": "maria.garcia@example.com"},
    {"id": "CLIENT-002", "name": "Juan Perez",      "email": "juan.perez@example.com"},
    {"id": "CLIENT-003", "name": "Ana Lopez",       "email": "ana.lopez@example.com"},
    {"id": "CLIENT-004", "name": "Carlos Ruiz",     "email": "carlos.ruiz@example.com"},
    {"id": "CLIENT-005", "name": "Elena Martinez",  "email": "elena.martinez@example.com"},
    {"id": "CLIENT-006", "name": "David Sanchez",   "email": "david.sanchez@example.com"},
    {"id": "CLIENT-007", "name": "Laura Fernandez", "email": "laura.fernandez@example.com"},
    {"id": "CLIENT-008", "name": "Roberto Jimenez", "email": "roberto.jimenez@example.com"},
]

CLAIM_TEXTS = {
    "danys_propis": [
        "Mi vehiculo sufrio danos en el parking de un centro comercial. Adjunto fotos y factura del taller.",
        "Tuve un accidente de aparcamiento donde golpee una columna. La reparacion ya ha sido realizada.",
        "Granizo de gran tamano dano la carroceria y cristales de mi coche. Tengo todos los justificantes.",
        "Colision en marcha atras contra un poste. Solicito cobertura segun mi poliza a todo riesgo.",
    ],
    "responsabilitat": [
        "Provoque un accidente con otro vehiculo al cambiar de carril. El tercero solicita compensacion.",
        "Atropelle accidentalmente a un peaton que se cruzo fuera del paso. Adjunto acta policial.",
        "Colisione con otro vehiculo en una rotonda. La responsabilidad es mia segun el acta.",
    ],
    "robatori": [
        "Sufri el robo de mi vehiculo en plena via publica. Tengo denuncia policial y listado de objetos.",
        "Me robaron el coche del garaje comunitario. Adjunto acta y lista detallada del contenido.",
    ],
    "danys_mecanics": [
        "El motor de mi vehiculo ha sufrido una averia grave. Solicito cobertura segun mi poliza.",
        "Problema mecanico en la transmision. Adjunto informe del taller con el diagnostico.",
    ],
}


def generate_claim_id(index: int) -> str:
    """Genera ID unico con formato CLM-DATASET-NNN."""
    return f"CLM-DATASET-{index:03d}"


def random_date_recent(days_back: int = 30) -> str:
    """Fecha aleatoria en los ultimos N dias."""
    offset = random.randint(0, days_back)
    date   = datetime.utcnow() - timedelta(days=offset)
    return date.isoformat()


def build_claim(
    claim_id:       str,
    claim_type:     str,
    amount:         float,
    docs_complete:  bool = True,
    drop_doc:       str  | None = None,
    client_override: dict | None = None,
    scenario_label: str  = "",
) -> dict:
    """Construye un siniestro sintetico."""
    client = client_override or random.choice(CLIENT_POOL)
    all_required_docs = CLAIM_TYPES[claim_type]

    if docs_complete:
        documents = list(all_required_docs)
    elif drop_doc:
        documents = [d for d in all_required_docs if d != drop_doc]
    else:
        # Quita 1 o 2 documentos aleatorios
        n_to_drop = random.randint(1, min(2, len(all_required_docs) - 1))
        documents = random.sample(all_required_docs, len(all_required_docs) - n_to_drop)

    text = random.choice(CLAIM_TEXTS[claim_type])

    return {
        "claim_id":         claim_id,
        "client_id":        client["id"],
        "client_email":     client["email"],
        "client_name":      client["name"],
        "claim_type":       claim_type,
        "channel":          random.choice(CHANNELS),
        "amount_requested": round(amount, 2),
        "documents":        documents,
        "text":             text,
        "created_at":       random_date_recent(),
        "scenario":         scenario_label,
    }


def generate_dataset() -> list[dict]:
    """Genera 30 casos cubriendo todos los escenarios."""
    claims: list[dict] = []
    idx = 1

    # ── Bloque 1: Pago automatico (10 casos) ──────────────────────────────
    # Cobertura OK, importe bajo, documentos completos
    pago_auto_cases = [
        ("danys_propis",    1500),
        ("danys_propis",    2300),
        ("danys_propis",    3800),
        ("danys_propis",    4500),
        ("responsabilitat", 1200),
        ("responsabilitat", 2800),
        ("responsabilitat", 4900),
        ("robatori",        1800),
        ("robatori",        3500),
        ("robatori",        4700),
    ]
    for claim_type, amount in pago_auto_cases:
        claims.append(build_claim(
            claim_id       = generate_claim_id(idx),
            claim_type     = claim_type,
            amount         = amount,
            docs_complete  = True,
            scenario_label = "pago_automatico",
        ))
        idx += 1

    # ── Bloque 2: Revision humana HITL (6 casos) ──────────────────────────
    # Cobertura OK, importe alto (>5000), documentos completos
    hitl_cases = [
        ("danys_propis",    7500),
        ("danys_propis",    9200),
        ("responsabilitat", 15000),
        ("responsabilitat", 25000),
        ("responsabilitat", 40000),
        ("robatori",        6500),
    ]
    for claim_type, amount in hitl_cases:
        claims.append(build_claim(
            claim_id       = generate_claim_id(idx),
            claim_type     = claim_type,
            amount         = amount,
            docs_complete  = True,
            scenario_label = "hitl",
        ))
        idx += 1

    # ── Bloque 3: Rechazo por no cobertura (4 casos) ──────────────────────
    # Tipo no cubierto (danys_mecanics)
    rechazo_cases = [
        ("danys_mecanics", 800),
        ("danys_mecanics", 2200),
        ("danys_mecanics", 3500),
        ("danys_mecanics", 1500),
    ]
    for claim_type, amount in rechazo_cases:
        claims.append(build_claim(
            claim_id       = generate_claim_id(idx),
            claim_type     = claim_type,
            amount         = amount,
            docs_complete  = True,
            scenario_label = "rechazo_no_cobertura",
        ))
        idx += 1

    # ── Bloque 4: Solicitud de informacion (8 casos) ──────────────────────
    # Documentacion incompleta de varios tipos
    info_cases = [
        ("danys_propis",    2500, "factura"),
        ("danys_propis",    3000, "denuncia_companyia"),
        ("danys_propis",    1800, "foto_danys"),
        ("responsabilitat", 4500, "dades_tercer"),
        ("responsabilitat", 6800, "acta_policial"),
        ("robatori",        2200, "llista_objectes_robats"),
        ("robatori",        3300, "acta_policial"),
        ("danys_propis",    2800, "factura"),
    ]
    for claim_type, amount, doc_missing in info_cases:
        claims.append(build_claim(
            claim_id       = generate_claim_id(idx),
            claim_type     = claim_type,
            amount         = amount,
            docs_complete  = False,
            drop_doc       = doc_missing,
            scenario_label = "info_incompleta",
        ))
        idx += 1

    # ── Bloque 5: Casos limite para fraude (2 casos) ──────────────────────
    # Cliente generado aleatoriamente con ID sospechoso e importes inusuales
    suspicious_client = {
        "id":    "CLIENT-SUSPECT-001",
        "name":  "Cliente Sospechoso",
        "email": "anonimo@temporal.com",
    }
    claims.append(build_claim(
        claim_id        = generate_claim_id(idx),
        claim_type      = "danys_propis",
        amount          = 9999.99,
        docs_complete   = True,
        client_override = suspicious_client,
        scenario_label  = "potencial_fraude",
    ))
    idx += 1
    claims.append(build_claim(
        claim_id        = generate_claim_id(idx),
        claim_type      = "robatori",
        amount          = 7777.77,
        docs_complete   = True,
        client_override = suspicious_client,
        scenario_label  = "potencial_fraude",
    ))
    idx += 1

    return claims


def write_json(claims: list[dict], path: Path) -> None:
    """Escribe el dataset completo en JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(claims, f, ensure_ascii=False, indent=2)
    print(f"  JSON escrito: {path} ({len(claims)} casos)")


def write_csv_summary(claims: list[dict], path: Path) -> None:
    """Escribe un CSV resumen para inspeccion rapida."""
    fields = [
        "claim_id", "scenario", "client_id", "claim_type",
        "amount_requested", "channel", "documents", "created_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for c in claims:
            row = c.copy()
            row["documents"] = ",".join(c["documents"])
            writer.writerow(row)
    print(f"  CSV escrito:  {path}")


def print_stats(claims: list[dict]) -> None:
    """Estadisticas del dataset generado."""
    from collections import Counter

    print()
    print("Resumen del dataset:")
    print(f"  Total casos: {len(claims)}")
    print()
    print("  Por escenario:")
    for scenario, n in Counter(c["scenario"] for c in claims).most_common():
        print(f"    {scenario:25s} {n:3d}")
    print()
    print("  Por tipo de siniestro:")
    for claim_type, n in Counter(c["claim_type"] for c in claims).most_common():
        print(f"    {claim_type:25s} {n:3d}")
    print()
    print("  Por canal:")
    for channel, n in Counter(c["channel"] for c in claims).most_common():
        print(f"    {channel:25s} {n:3d}")
    print()
    amounts = [c["amount_requested"] for c in claims]
    print(f"  Importes: min={min(amounts):.2f} EUR  max={max(amounts):.2f} EUR  "
          f"medio={sum(amounts) / len(amounts):.2f} EUR")
    print()


def main() -> int:
    print("Generando dataset sintetico de siniestros...")
    print()

    claims = generate_dataset()

    json_path = OUTPUT_DIR / "claims_dataset.json"
    csv_path  = OUTPUT_DIR / "claims_dataset.csv"

    write_json(claims, json_path)
    write_csv_summary(claims, csv_path)

    print_stats(claims)
    print("Dataset generado correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
