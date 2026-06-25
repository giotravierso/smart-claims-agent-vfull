"""
Herramientas de detección de fraude para el Agente G.

Implementa cuatro detectores deterministas:
  1. Verificación OFAC/ONU — fuzzy matching contra lista de sanciones mock
  2. Anomalía de importe    — Z-score frente a histórico por tipo de siniestro
  3. Duplicados recientes   — mismo cliente/tipo en ventana temporal configurable
  4. Coherencia documental  — inconsistencias de fechas entre documentos

Diseño determinista para garantizar auditabilidad de cada señal de fraude.
En producción, la lista OFAC se descargaria periodicamente del servicio
oficial y los baselines de importe se calcularian desde la BD histórica.
"""
from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import NamedTuple

logger = logging.getLogger(__name__)


# ── Lista de sanciones mock (simulación OFAC SDN + lista ONU) ─────────────────

_SANCTIONS_LIST: list[dict] = [
    {"id": "OFAC-001", "name": "Al-Rashid Trading Group",        "type": "entity",     "list": "SDN"},
    {"id": "OFAC-002", "name": "Viktor Nikolaev Kozlov",         "type": "individual", "list": "SDN"},
    {"id": "OFAC-003", "name": "Amira Belhaj",                   "type": "individual", "list": "SDN"},
    {"id": "OFAC-004", "name": "Crescent Star Holdings Ltd",     "type": "entity",     "list": "SDN"},
    {"id": "OFAC-005", "name": "Dmitri Volkov",                  "type": "individual", "list": "SDN"},
    {"id": "OFAC-006", "name": "Al-Mawrid Finance Company",      "type": "entity",     "list": "SDN"},
    {"id": "OFAC-007", "name": "Ramirez Fuentes Cartel",         "type": "entity",     "list": "SDN"},
    {"id": "OFAC-008", "name": "Yusuf Ibrahim Al-Farsi",         "type": "individual", "list": "ONU"},
    {"id": "OFAC-009", "name": "Eastern Silk Route Investments", "type": "entity",     "list": "ONU"},
    {"id": "OFAC-010", "name": "Bogdan Petrescu",                "type": "individual", "list": "SDN"},
    {"id": "OFAC-011", "name": "Black Sea Capital Partners",     "type": "entity",     "list": "SDN"},
    {"id": "OFAC-012", "name": "Mohammed Al-Hashimi",            "type": "individual", "list": "ONU"},
    {"id": "OFAC-013", "name": "Grupo Financiero Centauro",      "type": "entity",     "list": "SDN"},
    {"id": "OFAC-014", "name": "Natalia Semenova",               "type": "individual", "list": "SDN"},
    {"id": "OFAC-015", "name": "Falcon Ridge Resources Corp",    "type": "entity",     "list": "SDN"},
]

_AMOUNT_BASELINES: dict[str, dict] = {
    "danys_propis":    {"mean": 2800.0,  "std": 1400.0,  "max_legitimate": 9000.0},
    "responsabilitat": {"mean": 12000.0, "std": 8000.0,  "max_legitimate": 48000.0},
    "robatori":        {"mean": 3200.0,  "std": 1600.0,  "max_legitimate": 7500.0},
    "danys_mecanics":  {"mean": 800.0,   "std": 400.0,   "max_legitimate": 3000.0},
    "_default":        {"mean": 3000.0,  "std": 2000.0,  "max_legitimate": 10000.0},
}

_OFAC_MATCH_THRESHOLD = 0.82
_ZSCORE_THRESHOLD = 2.0


# ── Resultados tipados ────────────────────────────────────────────────────────

class OFACResult(NamedTuple):
    matched: bool
    entity_id: str | None
    entity_name: str | None
    similarity: float
    sanction_list: str | None


class AmountResult(NamedTuple):
    flagged: bool
    z_score: float
    requested: float
    mean: float
    std: float
    exceeded_max: bool


class DuplicateResult(NamedTuple):
    found: bool
    matching_claim_ids: list[str]
    days_since_last: int | None


class DocCoherenceResult(NamedTuple):
    incoherent: bool
    issues: list[str]


# ── Utilidades internas ───────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    ascii_text = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return " ".join(ascii_text.split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ── Detector 1: Verificación OFAC/ONU ────────────────────────────────────────

def check_ofac_sanctions(client_name: str) -> OFACResult:
    """Verifica el nombre del cliente contra la lista de sanciones."""
    if not client_name or not client_name.strip():
        return OFACResult(matched=False, entity_id=None, entity_name=None, similarity=0.0, sanction_list=None)

    best_score = 0.0
    best_entry: dict | None = None

    for entry in _SANCTIONS_LIST:
        score = _similarity(client_name, entry["name"])
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score >= _OFAC_MATCH_THRESHOLD and best_entry:
        logger.warning(
            "OFAC MATCH detectado: '%s' ~ '%s' (similitud=%.3f, lista=%s)",
            client_name, best_entry["name"], best_score, best_entry["list"],
        )
        return OFACResult(
            matched=True,
            entity_id=best_entry["id"],
            entity_name=best_entry["name"],
            similarity=round(best_score, 4),
            sanction_list=best_entry["list"],
        )

    return OFACResult(
        matched=False,
        entity_id=None,
        entity_name=None,
        similarity=round(best_score, 4),
        sanction_list=None,
    )


# ── Detector 2: Anomalía de importe ──────────────────────────────────────────

def check_amount_anomaly(claim_type: str, amount: float) -> AmountResult:
    """Detecta importes estadísticamente anómalos comparando con el histórico."""
    baseline = _AMOUNT_BASELINES.get(claim_type, _AMOUNT_BASELINES["_default"])
    mean: float = baseline["mean"]
    std: float = baseline["std"]
    max_legit: float = baseline["max_legitimate"]

    z_score = (amount - mean) / std if std > 0 else 0.0
    exceeded_max = amount > max_legit
    flagged = abs(z_score) > _ZSCORE_THRESHOLD or exceeded_max

    if flagged:
        logger.info(
            "Importe anomalo: %.2f EUR | tipo=%s | Z=%.2f | max_legitimo=%.2f EUR",
            amount, claim_type, z_score, max_legit,
        )

    return AmountResult(
        flagged=flagged,
        z_score=round(z_score, 3),
        requested=amount,
        mean=mean,
        std=std,
        exceeded_max=exceeded_max,
    )


# ── Detector 3: Duplicados recientes ─────────────────────────────────────────

def check_duplicate_claims(
    client_id: str,
    claim_type: str,
    existing_claims: list[dict],
    window_days: int = 90,
) -> DuplicateResult:
    """Detecta reclamaciones del mismo cliente y tipo en una ventana temporal."""
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    matches: list[str] = []
    min_days: int | None = None

    for claim in existing_claims:
        if claim.get("client_id") != client_id:
            continue
        if claim.get("claim_type") != claim_type:
            continue

        created_at = claim.get("created_at")
        if isinstance(created_at, str):
            created_at = _parse_date(created_at)

        if created_at and created_at >= cutoff:
            matches.append(claim["id"])
            days_ago = (datetime.utcnow() - created_at).days
            if min_days is None or days_ago < min_days:
                min_days = days_ago

    if matches:
        logger.info("Duplicados encontrados para cliente=%s tipo=%s: %s",
                    client_id, claim_type, matches)

    return DuplicateResult(
        found=bool(matches),
        matching_claim_ids=matches,
        days_since_last=min_days,
    )


# ── Detector 4: Coherencia documental ────────────────────────────────────────

def check_document_coherence(extracted_data: dict) -> DocCoherenceResult:
    """Detecta inconsistencias temporales entre documentos aportados."""
    issues: list[str] = []
    now = datetime.utcnow()

    incident_date = _parse_date(
        extracted_data.get("incident_date")
        or (extracted_data.get("acta_policial") or {}).get("incident_date")
    )
    claim_date = _parse_date(extracted_data.get("claim_date"))
    factura = extracted_data.get("factura")
    factura_date = _parse_date(
        factura.get("date") if isinstance(factura, dict) else extracted_data.get("factura_date")
    )

    if incident_date:
        if incident_date > now:
            issues.append(f"fecha_siniestro_futura:{incident_date.date()}")
        if incident_date < datetime(2015, 1, 1):
            issues.append(f"fecha_siniestro_muy_antigua:{incident_date.date()}")

    if incident_date and claim_date and claim_date < incident_date:
        issues.append(f"reclamacion_previa_al_siniestro:{claim_date.date()}<{incident_date.date()}")

    if factura_date and incident_date and factura_date < incident_date - timedelta(days=30):
        issues.append(f"factura_previa_al_siniestro:{factura_date.date()}")

    return DocCoherenceResult(incoherent=bool(issues), issues=issues)


# ── Scoring compuesto ─────────────────────────────────────────────────────────

def compute_risk_score(
    ofac: OFACResult,
    amount: AmountResult,
    duplicate: DuplicateResult,
    doc: DocCoherenceResult,
) -> tuple[float, str]:
    """
    Calcula la puntuación de riesgo compuesta y emite el veredicto graduado.

    Veredictos:
      BLOCKED     — OFAC match confirmado (rechazo automático)
      HIGH_RISK   — score >= 0.55 (HITL obligatorio)
      MEDIUM_RISK — score >= 0.25 (HITL recomendado)
      CLEAR       — score < 0.25 (continua el flujo)
    """
    if ofac.matched:
        return 1.0, "BLOCKED"

    score = 0.0

    if amount.exceeded_max:
        score += 0.40
    elif amount.flagged:
        score += min(abs(amount.z_score) / (_ZSCORE_THRESHOLD * 2.5), 0.35)

    if duplicate.found:
        recency = 1.0 if (duplicate.days_since_last or 90) < 30 else 0.65
        score += 0.35 * recency

    if doc.incoherent:
        score += min(len(doc.issues) * 0.10, 0.25)

    score = min(round(score, 3), 1.0)

    if score >= 0.55:
        verdict = "HIGH_RISK"
    elif score >= 0.25:
        verdict = "MEDIUM_RISK"
    else:
        verdict = "CLEAR"

    return score, verdict
