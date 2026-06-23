# Bitácora de trabajo — Smart-Claims Agent (TFM)

> Registro cronológico del trabajo realizado, pensado para explicar al equipo qué se ha
> hecho, por qué, y qué queda. Cada entrada indica: contexto, decisiones y cambios.
>
> **Convención mock vs. API real:** a lo largo del prototipo, las integraciones con los
> sistemas de Seguros Pepín están **simuladas (mock)** porque no tenemos acceso a sus APIs.
> Cada punto de simulación se marca con la nota `🔌 MOCK → API` explicando qué se haría con
> la integración real (qué sistema, qué endpoint, qué datos).

---

## 2026-06-23 — Sesión 1: análisis del repositorio y definición de plan

### Contexto de partida
- Estado real del repo: **esqueleto en fase temprana**. La documentación (README.md,
  CONTEXT_TFM.md) marcaba muchos componentes como "✅ Operativo" pero el código estaba
  en su mayoría sin implementar.
- Aclaraciones del equipo (recogidas esta sesión):
  - **Seguros Pepín es una empresa REAL** (la doc la llamaba "ficticia" — desactualizado).
  - **No tendremos acceso a las APIs de sus sistemas** → las integraciones externas se
    quedan como mock de forma **definitiva**, no temporal.
  - El **entregable de la Entrega 2 (26/06/2026)** es principalmente la **memoria escrita**:
    capítulos de **Arquitectura**, **Herramientas** y **Manual de usuario**. Adicionalmente
    se continúa el prototipo. Normativa APA 7.ª, en castellano.
  - La **UX/frontend no es prioritaria** ahora.

### Diagnóstico técnico (qué funcionaba y qué no)
| Componente | Estado real encontrado |
|---|---|
| Infra Docker (5 servicios) | ✅ Bien definida (`docker-compose.yml`) |
| 8 mock tools (`claim_tools.py`) | ✅ Completas y bien documentadas — lo más maduro |
| Orquestador "Agente A" | ⚠️ Grafo LangGraph parcial; agentes B–G son *stubs* vacíos |
| API REST `POST /claims` | ❌ Devuelve mensaje fijo, NO invoca al orquestador |
| `init_db()` | ❌ No crea el esquema (cuerpo vacío) |
| Agentes B, C, D, E, G | ❌ Sin implementar (`_stub` que devuelve `{}`) |
| Ciclo ReAct real | ❌ `triage` enruta una vez; los nodos no vuelven al orquestador |
| Bug de routing | ❌ Enruta a tool `resolve_claim` que no existe |
| Capa BD duplicada | ⚠️ `backend/db/` y `backend/app/db/` repetidas |
| Frontend Streamlit | ❌ Una línea con error de sintaxis (`st.titgle`) — irrelevante ahora |

### Decisión de enfoque
**Construir primero, documentar después.** Orden acordado con el equipo:
1. Completar el prototipo: implementar agentes B–G y la orquestación ReAct end-to-end,
   conectados a las mock tools, con persistencia de decisiones en MariaDB.
2. Redactar los tres capítulos de memoria sobre el prototipo ya funcional.

Razón: el Manual de usuario y el capítulo de Arquitectura deben describir un flujo que
realmente se ejecuta; así los ejemplos y capturas son reales.

### Pendiente al cierre de esta entrada
- [ ] Arreglar bloqueantes: `init_db`, conexión API→orquestador, bug routing `resolve_claim`.
- [ ] Implementar agentes B, C, D, E, G como nodos LangGraph con ciclo ReAct.
- [ ] Persistir decisiones de agentes (tabla `agent_decisions`).
- [ ] Consolidar capa BD duplicada.
- [ ] Redactar memoria: Arquitectura, Herramientas, Manual de usuario.

### Modo de trabajo (acordado esta sesión)
- Rama de trabajo: `feature/prototipo-e2e-entrega2` (no se toca `main` directamente).
- Ejecución por **subagentes** (un implementador por tarea + revisión), siguiendo el plan en
  `docs/superpowers/plans/2026-06-23-prototipo-e2e-y-memoria-entrega2.md`.
- Entorno local: Python 3.11 vía `py`; **Docker no disponible** aquí → la verificación E2E se
  hace con `pytest` + la CLI de demo, no con `docker compose`.

---

## 2026-06-23 — Sesión 1 (cont.): Fase 0 — Cimientos ✅

- **Eliminada la capa BD duplicada**: borrados `backend/db/models.py` y `backend/db/session.py`
  (eran copias muertas; el código activo usa `app.db.*`). Se conserva `backend/db/init.sql`
  porque lo monta Docker. *(commit e18ca33)*
- **`init_db()` ahora crea el esquema** con `Base.metadata.create_all` (idempotente). Antes no
  hacía nada, por lo que en ejecución local/tests no existían las tablas. *(commit 23cac55)*
- Verificado: los imports `app.db.models` / `app.db.session` resuelven sin conectar a MariaDB
  (el engine async es perezoso).

## 2026-06-23 — Sesión 1 (cont.): Fase 1 — Persistencia ✅

- **Nuevo `backend/app/db/repository.py`** con tres funciones async:
  `save_claim` (alta idempotente de expediente), `log_agent_decision` (registra una decisión y
  devuelve su id) y `get_claim_with_decisions` (devuelve el expediente + sus decisiones ordenadas).
  Esto da la **trazabilidad/auditoría** de cada decisión de los agentes en MariaDB. *(commit 8574026)*
- **Tests con SQLite en memoria** (`backend/tests/`): no dependen de MariaDB ni de Docker, así que
  corren en cualquier máquina. Se añadió `backend/pytest.ini` (`asyncio_mode=auto`, `pythonpath=.`).
  El repositorio accede a la sesión vía atributo de módulo para que los tests puedan sustituir la
  BD por SQLite — patrón clave para poder testear sin la base real.
- Estado tests: **3/3 verde**. Revisado por subagente independiente (spec ✅, calidad aprobada).

## 2026-06-23 — Sesión 1 (cont.): Fase 2 — Razonamiento ✅

- **Nuevo `backend/app/agents/reasoning.py`** con `reason(system, prompt, fallback)`. Si hay
  `ANTHROPIC_API_KEY`, genera el razonamiento (CoT) con Claude (`claude-sonnet-4-20250514`); si no
  la hay —o si la llamada falla— devuelve un *fallback* determinista. **La demo funciona siempre**,
  con o sin clave de API (mitiga el riesgo de fallo en defensa en vivo). *(commit 595d222)*
- Tests: 2 nuevos (fallback sin clave; fallback ante error del LLM). Suite total **5/5 verde**.
- Nota para el equipo: el modelo `claude-sonnet-4-20250514` se mantiene por consistencia con el
  código existente; se podría actualizar a `claude-sonnet-4-6` (más reciente) si interesa.

## 2026-06-23 — Sesión 1 (cont.): Fase 3 — Agentes (en curso)

- Decisión de diseño: los agentes especialistas (B/C/D/G) son **funciones puras** (no escriben en BD);
  la persistencia se **centraliza** en `process_claim`. Cada agente registra su decisión en el estado
  (`decisions_log`) y su razonamiento (`reasoning_trace`). Beneficio: se testean sin base de datos.
- **Estado del grafo** (`backend/app/agents/state.py`): `ClaimState` con acumuladores
  (`reasoning_trace`, `decisions_log`) que se van concatenando a lo largo del flujo. *(commit 1cc378d)*
- **Agentes especialistas** (`backend/app/agents/specialists.py`): B (validación docs), C (extracción
  multimodal), D (cobertura), G (fraude). Cada uno invoca su mock tool y deja traza. Comentarios
  `🔌 MOCK → API` en cada uno indicando la integración real. **6 tests verde**. *(commit 1cc378d)*

## 2026-06-23 — Sesión 1 (cont.): Fase 3 — Orquestación ✅ (núcleo del prototipo)

- **Reescrito `backend/app/agents/orchestrator.py`**: Agente A (triaje), Agente E (resolución),
  nodo HITL, nodo de solicitud de información, y el **grafo LangGraph** que los conecta. *(commit 3cf5711)*
- **Flujo end-to-end real:** `A (triaje) → G (fraude) → B (docs) → C (extracción) → D (cobertura) → E (resolución)`
  con ramas condicionales:
  - Fraude marcado → REVISIÓN HUMANA (filtro temprano).
  - Faltan documentos → SOLICITUD DE INFO al cliente (y fin).
  - Sin cobertura → RECHAZO.
  - Importe > umbral HITL (5000€, configurable) → REVISIÓN HUMANA.
  - Si todo OK e importe ≤ umbral → PAGO automático.
- **`process_claim(...)`** ejecuta el grafo y **persiste todas las decisiones** en MariaDB (envuelto en
  try/except: si no hay BD —p. ej. la CLI sin Docker— el flujo igual devuelve el resultado).
- **6 tests E2E** cubren los 5 caminos (PAGO, RECHAZO, REVISIÓN por importe, SOLICITUD info, REVISIÓN por
  fraude) + persistencia. La aleatoriedad del fraude se fija en los tests para que sean deterministas.
- Suite total: **17/17 verde**. Revisado por subagente independiente (spec ✅, calidad aprobada, sin bugs).

## 2026-06-23 — Sesión 1 (cont.): Fase 4 — Exposición + Fase 5 — Verificación ✅

- **API conectada al orquestador** (`backend/app/routers/claims.py`): `POST /api/v1/claims` ahora
  ejecuta `process_claim(...)` y devuelve la decisión, el razonamiento (CoT) y si requiere HITL.
  `GET /api/v1/claims/{id}` consulta MariaDB y devuelve el expediente con sus decisiones (404 si no
  existe). `/api/v1/agents/status` ya reporta los 6 agentes como `implemented`. *(commit 885fec4)*
- **CLI de demostración** (`backend/scripts/run_demo.py`): ejecuta 4 expedientes representativos y
  muestra el Chain of Thought + la decisión de cada uno. No requiere base de datos ni Docker. Útil
  para la defensa y para las capturas del Manual de usuario.
- **Reproducibilidad**: se fijó `random.seed(20)` en la demo para que el mock de fraude (aleatorio)
  dé siempre el mismo camino ante el tribunal. *(commit 762d0b0)*
- **Verificación E2E** (sin Docker): la demo produce los 4 caminos esperados →
  `DEMO-PAGO → PAGO`, `DEMO-HITL → REVISIÓN_HUMANA`, `DEMO-RECHAZO → RECHAZO`,
  `DEMO-INFO → SOLICITUD_INFO`. Los avisos "no se pudo persistir" son esperados (sin MariaDB local)
  y el flujo continúa igualmente (resiliencia diseñada a propósito).
- **Suite de tests: 20/20 verde** (3 repo + 2 razonamiento + 6 agentes + 6 orquestación + 3 API).

### Estado del prototipo: FUNCIONAL END-TO-END ✅
El proceso completo de gestión de un siniestro se ejecuta de principio a fin con mocks. Listo para
documentar la memoria (Arquitectura, Herramientas, Manual de usuario).

## 2026-06-23 — Sesión 1 (cont.): Fase 6 — Memoria Entrega 2 ✅

Redactados los tres capítulos de la memoria (castellano, profundidad media, citas APA 7.ª integradas).
Es **solo contenido en Markdown**; el formato Word lo dará Claude app después. Carpeta `docs/memoria/`:

- **`01-arquitectura.md`** (~2.600 palabras): 5 capas + 2 transversales, patrón orquestador-trabajadores
  y su justificación, los 6 agentes, flujo con ramas, estado y ciclo, modelo de datos (3 tablas), HITL,
  decisiones de diseño, tabla **Mock → Integración real**, despliegue y stack. Diagramas ASCII + 6 tablas.
- **`02-herramientas.md`** (~2.700 palabras): catálogo de las 8 tools (propósito, E/S, agente que la usa,
  y qué sería la integración real en producción), estrategia de simulación, tabla consolidada Mock→Real.
- **`03-manual-usuario.md`** (~3.700 palabras): requisitos, `.env`, arranque Docker, uso vía API (ejemplos
  `curl` por los 4 caminos), uso vía CLI sin Docker, interpretación de resultados, inspección con Adminer,
  resolución de problemas. Verificado contra el código real.

### Discrepancias honestas detectadas al documentar (para revisar por el equipo)
- `hitl_feedback` existe en `init.sql` pero **no tiene modelo SQLAlchemy** → con `create_all` (local/tests)
  no se crea; solo en Docker vía `init.sql`. En el MVP la tabla queda vacía (HITL feedback no implementado).
- El campo `text` de `ClaimRequest` (API) **no se pasa** a `process_claim` actualmente.
- Unificar en revisión de formato la cita "LangGraph AI / LangChain AI (2024)" (nombre de autor).

### Correcciones de documentación
- `CONTEXT_TFM.md` y `generate_project_overview.py`: **"empresa ficticia" → empresa real**.
- `CONTEXT_TFM.md`: estados de agentes B–G actualizados a "✅ implementado (mock)" y checklist de Entrega 2.

### Cierre de la Entrega 2
Prototipo funcional E2E (20 tests verde) + 3 capítulos de memoria redactados. Rama
`feature/prototipo-e2e-entrega2`. Pendiente del equipo: dar formato Word a la memoria, revisar las
discrepancias anotadas, y (fases siguientes) dataset sintético, ingesta RAG real y dashboard Streamlit.
