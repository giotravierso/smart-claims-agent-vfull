# Plan de implementación — Prototipo E2E + Memoria Entrega 2

> **Para ejecutores agénticos:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea a tarea. Los pasos usan checkbox (`- [ ]`) para seguimiento.

**Goal:** Dejar el prototipo Smart-Claims ejecutable de extremo a extremo con mocks (API → orquestador → agentes B–G → decisión → persistencia) y redactar los tres capítulos de memoria de la Entrega 2 (Arquitectura, Herramientas, Manual de usuario).

**Architecture:** Patrón *orquestador-trabajadores* sobre LangGraph. El Agente A (orquestador) razona el triaje con CoT; los agentes B/C/D/G son nodos deterministas que invocan mock tools y registran su decisión en MariaDB; el Agente E aplica la lógica de resolución (PAGO / RECHAZO / HITL) según cobertura y umbral. El LLM (Claude) es **opcional**: si hay `ANTHROPIC_API_KEY` enriquece el razonamiento de A/E; si no, hay *fallback* determinista para que la demo siempre corra.

**Tech Stack:** Python 3.11, FastAPI, LangGraph + LangChain, SQLAlchemy 2.0 async + aiomysql, MariaDB 11.3, ChromaDB (RAG, fase posterior), Docker Compose, pytest + pytest-asyncio.

**Convención transversal:** cada punto de simulación lleva el comentario `🔌 MOCK → API:` indicando qué sistema real de Seguros Pepín lo sustituiría, con qué endpoint/datos. Toda decisión de diseño y avance se anota en `docs/BITACORA.md`.

---

## Estructura de archivos

**Backend (prototipo):**
- `backend/app/db/session.py` — *modificar*: `init_db()` debe crear el esquema; helper de sesión.
- `backend/app/db/repository.py` — *crear*: funciones de persistencia (`save_claim`, `log_agent_decision`, `get_claim_with_decisions`).
- `backend/app/agents/reasoning.py` — *crear*: helper LLM opcional con *fallback* determinista (genera CoT).
- `backend/app/agents/state.py` — *crear*: `ClaimState` (TypedDict) compartido por el grafo.
- `backend/app/agents/specialists.py` — *crear*: nodos B (validación), C (extracción), D (cobertura), G (fraude).
- `backend/app/agents/orchestrator.py` — *modificar*: triaje (A), resolución (E), HITL, *wiring* del grafo y enrutamiento.
- `backend/app/routers/claims.py` — *modificar*: `POST /claims` invoca el orquestador; `GET /{id}` consulta MariaDB.
- `backend/app/routers/agents.py` — *modificar*: `/status` refleja agentes implementados.
- `backend/scripts/run_demo.py` — *crear*: CLI de demostración que procesa un expediente y muestra el CoT y la decisión.
- `backend/db/models.py`, `backend/db/session.py` — *eliminar*: duplicados muertos (el código activo usa `app.db.*`; `backend/db/init.sql` se conserva).
- `backend/requirements.txt` — *modificar*: añadir `pytest`, `pytest-asyncio`; quitar `pymysql` (no usado) o dejar comentado.

**Tests:**
- `backend/tests/test_tools.py` — *crear*: contratos de las mock tools.
- `backend/tests/test_agents.py` — *crear*: cada nodo agente devuelve la forma esperada.
- `backend/tests/test_orchestration.py` — *crear*: flujo E2E por los tres caminos (PAGO / RECHAZO / HITL).

**Memoria (contenido, sin formato — el formato Word lo hace Claude app después):**
- `docs/memoria/01-arquitectura.md` — *crear*.
- `docs/memoria/02-herramientas.md` — *crear*.
- `docs/memoria/03-manual-usuario.md` — *crear*.

---

## FASE 0 — Cimientos (desbloquear el flujo)

### Task 0.1: Eliminar la capa BD duplicada

**Files:**
- Delete: `backend/db/models.py`
- Delete: `backend/db/session.py`

- [ ] **Step 1:** Verificar que nada importa `from db.models`/`from db.session` (solo se usa `app.db.*`).

Run: `grep -rn "from db\.\|import db\." backend/app` → Esperado: sin resultados.

- [ ] **Step 2:** Eliminar los dos archivos duplicados (conservar `backend/db/init.sql`).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: eliminar capa BD duplicada (backend/db/models.py, session.py)"
```

### Task 0.2: `init_db()` crea el esquema

**Files:**
- Modify: `backend/app/db/session.py`

- [ ] **Step 1:** Importar los modelos y crear tablas en `init_db()`.

```python
async def init_db():
    """Crea el esquema si no existe (idempotente). En Docker, init.sql ya lo
    crea; esto cubre ejecución local/tests y mantiene SQLAlchemy como fuente."""
    from app.db import models  # noqa: F401 — registra las tablas en Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 2:** Commit.

```bash
git add backend/app/db/session.py && git commit -m "fix: init_db crea el esquema con Base.metadata.create_all"
```

---

## FASE 1 — Persistencia (auditoría de decisiones)

### Task 1.1: Repositorio de persistencia

**Files:**
- Create: `backend/app/db/repository.py`
- Test: `backend/tests/test_repository.py`

- [ ] **Step 1: Escribir el test que falla** (usa SQLite en memoria para no depender de MariaDB en tests).

```python
import pytest
from app.db.repository import log_agent_decision, get_claim_with_decisions

@pytest.mark.asyncio
async def test_log_and_read_decision(seed_claim):
    await log_agent_decision(seed_claim, "agent_g", "check_fraud",
                             "Riesgo bajo, sin coincidencia OFAC", confidence=0.95)
    claim = await get_claim_with_decisions(seed_claim)
    assert len(claim["decisions"]) == 1
    assert claim["decisions"][0]["agent"] == "agent_g"
```

- [ ] **Step 2:** Ejecutar y verificar que falla (módulo inexistente).

Run: `cd backend && pytest tests/test_repository.py -v` → Esperado: ImportError.

- [ ] **Step 3: Implementar** `repository.py` con `save_claim`, `log_agent_decision`, `get_claim_with_decisions` usando `AsyncSessionLocal`.

- [ ] **Step 4:** Ejecutar test → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/repository.py backend/tests/ && git commit -m "feat: repositorio de persistencia de decisiones de agentes"
```

---

## FASE 2 — Razonamiento (LLM opcional con fallback)

### Task 2.1: Helper de razonamiento

**Files:**
- Create: `backend/app/agents/reasoning.py`
- Test: `backend/tests/test_reasoning.py`

- [ ] **Step 1: Test que falla** — sin API key, `reason()` devuelve el *fallback* determinista pasado.

```python
from app.agents.reasoning import reason

def test_reason_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = reason(system="...", prompt="...", fallback="DECISIÓN: pago")
    assert out == "DECISIÓN: pago"
```

- [ ] **Step 2:** Ejecutar → FAIL.

- [ ] **Step 3: Implementar** `reason(system, prompt, fallback)`:
  - Si no hay `ANTHROPIC_API_KEY` → devuelve `fallback`.
  - Si hay → llama a `ChatAnthropic(model="claude-sonnet-4-20250514")` y devuelve el texto; ante cualquier excepción, *fallback*.

- [ ] **Step 4:** Ejecutar → PASS.

- [ ] **Step 5: Commit.**

---

## FASE 3 — Agentes y orquestación

### Task 3.1: Estado compartido del grafo

**Files:**
- Create: `backend/app/agents/state.py`

- [ ] **Step 1:** Mover `ClaimState` (TypedDict) a `state.py` con campos:
  `claim_id, client_id, claim_type, amount_requested, channel, doc_types,
  messages, status, validation, extraction, policy_check, fraud_check,
  decision, reasoning_trace (list[str]), hitl_required`.
- [ ] **Step 2:** Commit.

### Task 3.2: Agentes especialistas B, C, D, G

**Files:**
- Create: `backend/app/agents/specialists.py`
- Test: `backend/tests/test_agents.py`

- [ ] **Step 1: Tests que fallan** — uno por agente, verificando la clave que añade al estado:

```python
from app.agents.specialists import agent_b_validate, agent_d_policy

@pytest.mark.asyncio
async def test_agent_d_marks_coverage():
    state = {"claim_id": "CLM-X", "claim_type": "danys_propis",
             "amount_requested": 3200.0, "reasoning_trace": []}
    out = await agent_d_policy(state)
    assert out["policy_check"]["covered"] is True
```

- [ ] **Step 2:** Ejecutar → FAIL.

- [ ] **Step 3: Implementar** cada nodo async:
  - `agent_b_validate`: invoca `validate_documents`, añade `validation`, registra decisión, anota CoT. `🔌 MOCK → API: validación contra el gestor documental real de Seguros Pepín.`
  - `agent_c_extract`: invoca `extract_multimodal`. `🔌 MOCK → API: Claude Vision real sobre los adjuntos del expediente.`
  - `agent_d_policy`: invoca `check_policy`. `🔌 MOCK → API: recuperación RAG sobre las pólizas reales en ChromaDB (fase posterior).`
  - `agent_g_fraud`: invoca `check_fraud`. `🔌 MOCK → API: consulta a listas OFAC/ONU y motor antifraude corporativo.`
  - Cada uno llama a `log_agent_decision(...)` y hace `reasoning_trace.append(...)`.

- [ ] **Step 4:** Ejecutar → PASS.

- [ ] **Step 5: Commit.**

### Task 3.3: Orquestador (A), resolución (E), HITL y grafo

**Files:**
- Modify: `backend/app/agents/orchestrator.py`
- Test: `backend/tests/test_orchestration.py`

- [ ] **Step 1: Tests E2E que fallan** — tres caminos:

```python
@pytest.mark.asyncio
async def test_flow_auto_payment():   # cubierto, importe <= umbral
    res = await process_claim(claim_id="CLM-001", client_id="C-A",
        claim_type="danys_propis", amount_requested=3200.0,
        channel="email", doc_types=["foto_danys","factura","acta_policial"])
    assert res["decision"] == "PAGO"
    assert res["hitl_required"] is False

@pytest.mark.asyncio
async def test_flow_hitl_over_threshold():  # importe > 5000
    res = await process_claim(claim_id="CLM-002", client_id="C-B",
        claim_type="responsabilitat", amount_requested=8500.0,
        channel="web", doc_types=["foto_danys","factura","acta_policial"])
    assert res["hitl_required"] is True

@pytest.mark.asyncio
async def test_flow_rejection_no_coverage():  # tipo sin cobertura
    res = await process_claim(claim_id="CLM-9", client_id="C-Z",
        claim_type="danys_mecànics", amount_requested=1000.0,
        channel="email", doc_types=["foto_danys","factura","acta_policial"])
    assert res["decision"] == "RECHAZO"
```

- [ ] **Step 2:** Ejecutar → FAIL.

- [ ] **Step 3: Implementar:**
  - `triage_node` (A): genera CoT con `reason(...)` (fallback determinista), no rompe el flujo secuencial.
  - Grafo: `triage → agent_g → agent_b → agent_c → agent_d → resolve(E)` con aristas condicionales:
    - tras `agent_g`: si `fraud.is_flagged` → `hitl` (revisión) en vez de continuar.
    - tras `agent_b`: si faltan docs → `request_info` (mock) y `END`.
    - en `resolve` (E): `not covered` → `RECHAZO`; `amount > HITL_AMOUNT_THRESHOLD` → `hitl_required=True` + `PENDING_REVIEW`; si no → `PAGO` (invoca `approve_payment`).
  - `process_claim(claim_id, client_id, claim_type, amount_requested, channel, doc_types)` arma el estado inicial y hace `ainvoke`.
  - Umbral leído de `os.getenv("HITL_AMOUNT_THRESHOLD", "5000")`.

- [ ] **Step 4:** Ejecutar los 3 tests → PASS.

- [ ] **Step 5: Commit.**

---

## FASE 4 — Exposición (API + CLI demo)

### Task 4.1: Conectar API al orquestador

**Files:**
- Modify: `backend/app/routers/claims.py`
- Modify: `backend/app/routers/agents.py`

- [ ] **Step 1:** `POST /claims` → `await process_claim(...)`; devuelve `claim_id, status, decision, reasoning_trace, hitl_required`.
- [ ] **Step 2:** `GET /{claim_id}` → `get_claim_with_decisions(...)`.
- [ ] **Step 3:** `/agents/status` → todos `implemented`.
- [ ] **Step 4:** Commit.

### Task 4.2: CLI de demostración

**Files:**
- Create: `backend/scripts/run_demo.py`

- [ ] **Step 1:** Script que ejecuta `process_claim` sobre 3 expedientes de ejemplo (uno por camino) e imprime CoT + decisión. Sirve para la demo y para capturas del Manual de usuario.
- [ ] **Step 2:** Commit.

---

## FASE 5 — Verificación

### Task 5.1: Suite completa verde

- [ ] **Step 1:** `cd backend && pytest -v` → todos PASS.
- [ ] **Step 2:** `docker compose up -d` y prueba manual: `curl -X POST .../api/v1/claims` por los 3 caminos.
- [ ] **Step 3:** Anotar resultados (incl. capturas) en `docs/BITACORA.md`.
- [ ] **Step 4:** Commit.

---

## FASE 6 — Memoria Entrega 2 (contenido)

> Redacción en castellano, APA 7.ª, **solo contenido** (sin formato Word). Se apoya en el prototipo ya funcional. Cada apartado incluye nota de qué es mock y qué sería la integración real.

### Task 6.1: Capítulo Arquitectura — `docs/memoria/01-arquitectura.md`

- [ ] Secciones: (1) Visión general y 5 capas + 2 transversales; (2) Patrón orquestador-trabajadores y justificación (ReAct, reproducibilidad, coste); (3) Diagrama de flujo del expediente; (4) Decisiones de diseño (LangGraph vs LCEL, mocks definitivos, HITL, LLM opcional); (5) Modelo de datos (claims, agent_decisions, hitl_feedback); (6) Despliegue (5 servicios Docker). Tabla mock→API por integración externa.

### Task 6.2: Capítulo Herramientas — `docs/memoria/02-herramientas.md`

- [ ] Catálogo de las 8 tools con: propósito, firma (entrada/salida), agente que la usa, y `🔌 MOCK → API` (sistema real que la sustituiría). Tabla resumen + descripción por tool.

### Task 6.3: Capítulo Manual de usuario — `docs/memoria/03-manual-usuario.md`

- [ ] Requisitos previos; arranque con `docker compose up -d`; URLs de servicios; cómo lanzar un expediente vía API (ejemplos curl por los 3 caminos) y vía CLI demo; cómo interpretar el CoT y la decisión; cómo inspeccionar decisiones en Adminer. Capturas reales del prototipo.

### Task 6.4: Revisión y anotación final

- [ ] Releer los 3 capítulos contra el código real (que lo documentado exista). Actualizar `README.md`/`CONTEXT_TFM.md` para corregir "empresa ficticia" → real y estados desactualizados. Entrada final en `docs/BITACORA.md`.

---

## Auto-revisión del plan

- **Cobertura del spec:** los 3 capítulos de memoria (Arquitectura, Herramientas, Manual) → Fase 6. Prototipo ejecutable E2E → Fases 0–4. Verificación → Fase 5. ✓
- **Sin placeholders:** los pasos de código de las fases 0–4 incluyen código/firmas concretas; la fase 6 es contenido a redactar (su "código" es prosa, detallada por secciones). ✓
- **Consistencia de tipos:** `process_claim(claim_id, client_id, claim_type, amount_requested, channel, doc_types)` usado igual en tests (3.3) y API (4.1). `log_agent_decision` / `get_claim_with_decisions` consistentes entre 1.1, 3.2 y 4.1. ✓
