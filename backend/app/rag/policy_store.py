"""
Base de conocimiento RAG de pólizas (Agente D).

Indexa los documentos de póliza (data/policies/*.md) en ChromaDB EMBEBIDO
(en proceso, sin servidor) y permite recuperar la cláusula más relevante para
un siniestro mediante búsqueda vectorial. El Agente D usa esta recuperación
para decidir la cobertura citando la sección recuperada.

Las pólizas son SINTÉTICAS (placeholder del prototipo); en producción se
alimenta con las condiciones reales de Seguros Pepín. Si ChromaDB no está
disponible o la recuperación falla, el Agente D cae a la mock tool check_policy
(resiliencia: la demo nunca se rompe).
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

COLLECTION_NAME = "pepin_policies"

# Rutas candidatas a data/policies (local, Docker, etc.)
_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "data" / "policies",  # repo/backend/app/rag -> repo/data
    Path(__file__).resolve().parents[2] / "data" / "policies",  # /app/app/rag -> /app/data (Docker)
    Path("/app/data/policies"),
]

_collection = None          # caché de la colección ChromaDB
_load_failed = False        # si la carga falla una vez, no reintentar en bucle


def _policies_dir() -> Path | None:
    for c in _CANDIDATES:
        if c.is_dir():
            return c
    return None


def _parse_policy(path: Path) -> dict | None:
    """Lee un .md con frontmatter `--- key: value ---` + cuerpo en prosa."""
    text = path.read_text(encoding="utf-8")
    if not text.lstrip().startswith("---"):
        return None
    _, fm, body = text.split("---", 2)
    meta: dict = {}
    for line in fm.strip().splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip()
    # Normaliza tipos
    covered = str(meta.get("covered", "false")).lower() in ("true", "1", "yes", "sí", "si")
    try:
        max_cov = float(meta.get("max_coverage", 0) or 0)
        deduct = float(meta.get("deductible", 0) or 0)
    except ValueError:
        max_cov, deduct = 0.0, 0.0
    return {
        "claim_type":   meta.get("claim_type", "default"),
        "section":      meta.get("section", "póliza"),
        "covered":      covered,
        "max_coverage": max_cov,
        "deductible":   deduct,
        "summary":      meta.get("summary", "").strip(),
        "text":         body.strip(),
        "doc_id":       path.stem,
    }


def _build_collection():
    """Construye (una vez) la colección ChromaDB embebida con las pólizas."""
    global _collection, _load_failed
    if _collection is not None or _load_failed:
        return _collection

    pol_dir = _policies_dir()
    if pol_dir is None:
        logger.warning("RAG: no se encontró data/policies; se usará el fallback.")
        _load_failed = True
        return None

    try:
        import chromadb

        policies = [p for p in (_parse_policy(f) for f in sorted(pol_dir.glob("*.md"))) if p]
        if not policies:
            _load_failed = True
            return None

        client = chromadb.Client()  # embebido, en memoria
        col = client.get_or_create_collection(name=COLLECTION_NAME)
        col.add(
            ids=[p["doc_id"] for p in policies],
            # Texto indexado CONCISO y anclado en el claim_type (mejor recuperación
            # con el embedding ligero por defecto). El cuerpo completo queda en el .md.
            documents=[
                f"Siniestro tipo {p['claim_type']}. {p['claim_type']}. "
                f"{p['summary'] or p['text'][:160]}"
                for p in policies
            ],
            metadatas=[{
                "claim_type":   p["claim_type"],
                "section":      p["section"],
                "covered":      p["covered"],
                "max_coverage": p["max_coverage"],
                "deductible":   p["deductible"],
            } for p in policies],
        )
        _collection = col
        logger.info("RAG: %d pólizas indexadas en ChromaDB embebido.", len(policies))
        return _collection
    except Exception as exc:  # ChromaDB no disponible o error de indexado
        logger.warning("RAG: no se pudo construir el índice (%s); se usará el fallback.", exc)
        _load_failed = True
        return None


def retrieve_policy(claim_type: str, description: str = "") -> dict | None:
    """Recupera la póliza más relevante para el siniestro (búsqueda vectorial).

    Returns:
        dict con claim_type, section, covered, max_coverage, deductible,
        snippet y distance; o None si el RAG no está disponible.
    """
    col = _build_collection()
    if col is None:
        return None
    try:
        query = f"siniestro tipo {claim_type}: {description}".strip()
        # Recuperación vectorial filtrando por el tipo de siniestro (metadata
        # filtering). Robusto con corpus pequeño y escalable a varias cláusulas
        # por tipo (el embedding rankea la cláusula más relevante dentro del tipo).
        res = col.query(query_texts=[query], n_results=1, where={"claim_type": claim_type})
        if not res["ids"] or not res["ids"][0]:
            return None
        meta = res["metadatas"][0][0]
        doc  = res["documents"][0][0]
        dist = res["distances"][0][0] if res.get("distances") else None
        return {
            "claim_type":   meta.get("claim_type"),
            "section":      meta.get("section"),
            "covered":      bool(meta.get("covered")),
            "max_coverage": float(meta.get("max_coverage") or 0),
            "deductible":   float(meta.get("deductible") or 0),
            "snippet":      doc[:280],
            "distance":     round(float(dist), 3) if dist is not None else None,
        }
    except Exception as exc:
        logger.warning("RAG: fallo en la recuperación (%s); se usará el fallback.", exc)
        return None
