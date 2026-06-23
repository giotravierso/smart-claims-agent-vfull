# CONTEXT_TFM — Smart-Claims Agent

> **Uso de este fichero:** Adjúntalo como Knowledge Document al proyecto Claude del TFM.
> Actualiza las secciones marcadas con 🔄 cada vez que haya cambios.

---

## Identificación del proyecto

| Campo | Valor |
|-------|-------|
| **Título oficial** | Smart-Claims Agent: Sistema Agéntico de Procesamiento Multimodal y Ejecución Autónoma para la Gestión de Incidencias |
| **Institución** | OBS Business School |
| **Programa** | Máster en Machine Learning e Inteligencia Artificial |
| **Carga** | 10 ECTS |
| **Normativa** | APA 7.ª edición · Art. 5 (estructura) · Art. 7 (originalidad y citas) |
| **Edición** | 2510 (curso 2025–2026) |
| **Empresa de referencia** | Seguros Pepín, S.A. (empresa real; caso de uso real del sector asegurador) |
| **Repositorio** | https://github.com/[org]/TFM |

---

## Resumen ejecutivo del proyecto

Desarrollar un MVP de agente IA autónomo capaz de gestionar el ciclo completo de una reclamación de siniestro en el sector asegurador. El agente integra LLMs con capacidades de visión (VLM) y ejecución de herramientas (Function Calling) para analizar correos y documentos adjuntos, contrastarlos con políticas corporativas y ejecutar automáticamente la resolución óptima (pago, rechazo o solicitud de información), reduciendo la intervención manual en tareas de back-office.

---

## El problema

Las operaciones administrativas de Seguros Pepín (caso de uso principal: gestión de siniestros) sufren alta latencia por:

- Análisis manual de correos y validación física de documentos adjuntos (facturas, fotos, actas)
- Proceso propenso a errores humanos, costoso y difícil de escalar
- Cuellos de botella que afectan la satisfacción del cliente y la eficiencia operativa
- Controles de cumplimiento (OFAC, LA/FT) realizados como filtro de salida, no de entrada
- Falta de criterios estandarizados en la evaluación de cobertura

---

## La solución: arquitectura agéntica

Cinco capas funcionales más dos transversales:

### Capa 1 — Canales de entrada
- Email, portal web, WhatsApp (simulado), API REST

### Capa 2 — Orquestación (Agente A)
- LangGraph + ReAct · Gestión de estado por expediente
- Router de agentes · Human-in-the-Loop (HITL)

### Capa 3 — Agentes especializados
- **Agente A:** Orquestador LangGraph ✅ implementado
- **Agente B:** Validación documental ✅ implementado (mock)
- **Agente C:** Extracción multimodal VLM ✅ implementado (mock)
- **Agente D:** Verificación de cobertura RAG ✅ implementado (mock; RAG real en fase posterior)
- **Agente E:** Resolución autónoma ✅ implementado
- **Agente G:** Fraude y cumplimiento LA/FT ✅ implementado (mock)

### Capa 4 — Datos y conocimiento
- ChromaDB (pólizas, RAG) · MariaDB (log decisiones, HITL)

### Capa 5 — Integración simulada
- Mock APIs Python: pagos · notificaciones · sistemas legacy

### Transversal T1 — Seguridad
- Anonimización, control de acceso, auditoría

### Transversal T2 — Observabilidad
- Trazas CoT visibles, métricas, dashboard Streamlit

---

## Flujo de una reclamación

```
Cliente envía reclamación
        │
        ▼
[A] Orquestador — triaje y enrutamiento
        │
        ├──► [G] Verificación OFAC/fraude (filtro temprano)
        │
        ├──► [B] Validación documental
        │         └── ¿Faltan documentos? → solicitar al cliente
        │
        ├──► [C] Extracción VLM (fotos, facturas, actas)
        │
        ├──► [D] Verificación de cobertura via RAG
        │
        └──► [E] Decisión autónoma
                  ├── Importe ≤ umbral → PAGO automático
                  ├── Importe > umbral → HITL (revisión humana)
                  └── Sin cobertura   → RECHAZO justificado
```

---

## Stack tecnológico

| Componente | Tecnología | Estado |
|---|---|---|
| **LLM / VLM** | Claude Sonnet (claude-sonnet-4-20250514) | ✅ Decidido |
| **Framework agéntico** | LangGraph + LangChain | ✅ Decidido |
| **RAG (pólizas)** | ChromaDB + LangChain | ✅ Decidido |
| **Vector DB** | ChromaDB 0.5.3 (local) | ✅ Decidido |
| **Backend** | Python 3.11 + FastAPI + Uvicorn | ✅ Operativo |
| **ORM** | SQLAlchemy 2.0 + aiomysql (async) | ✅ Operativo |
| **Base de datos** | MariaDB 11.3 | ✅ Operativo |
| **APIs simuladas** | Python mock functions (@tool LangChain) | ✅ Implementado |
| **Frontend demo** | Streamlit 1.36 | ✅ Skeleton operativo |
| **Contenerización** | Docker + Compose (5 servicios) | ✅ Operativo |
| **OCR (fallback)** | Tesseract | ✅ Instalado |
| **llama-index** | Excluido del build inicial | 🔄 Se incorpora en S3 (ingesta RAG) |

---

## Herramientas (Mock APIs) implementadas

```python
tools = [
    "validate_documents(claim_id, doc_types) -> dict",
    "extract_multimodal(claim_id, file_url, doc_type) -> dict",
    "check_policy(claim_id, claim_type, amount) -> dict",
    "approve_payment(claim_id, amount, iban) -> dict",
    "send_rejection(claim_id, reason, client_email) -> dict",
    "request_more_info(claim_id, missing_fields, client_email) -> dict",
    "check_fraud(claim_id, client_id, amount) -> dict",
    "log_decision(claim_id, agent, reasoning, action) -> dict",
]
```

Todas decoradas con `@tool` de LangChain, invocables directamente por el LLM.

---

## KPIs y métricas de éxito

| Métrica | Descripción | Target |
|---|---|---|
| **Tasa de Resolución Autónoma** | % de casos finalizados sin intervención humana | 🔄 Por definir |
| **Reducción TAT** | Disminución del tiempo entrada → resolución | 🔄 Por definir |
| **Precisión extracción (F1-Score)** | Exactitud en captura de datos críticos de adjuntos | 🔄 Por definir |
| **Tasa de falsos positivos HITL** | % de casos enviados a revisión innecesariamente | 🔄 Por definir |

---

## Análisis de impacto y costes (diferenciador académico)

El proyecto incluye un módulo de simulación económica:

- **Costes técnicos:** consumo de tokens + cómputo (Docker local)
- **Ahorro estimado:** horas-empleado eliminadas por el sistema
- **ROI:** demostrar la viabilidad económica en un entorno empresarial real
- **Salida esperada:** informe comparativo coste/beneficio
- **Umbral HITL:** `HITL_AMOUNT_THRESHOLD=5000€` (configurable en `.env`)

---

## Estructura del documento TFM (Art. 5 normativa OBS)

```
1. Resumen ejecutivo          (1 página — OBLIGATORIO)
2. Introducción y justificación
3. Marco teórico
   3.1 IA Agéntica y patrón ReAct
   3.2 Multimodalidad en LLMs (VLM)
   3.3 RAG (Retrieval-Augmented Generation)
   3.4 Gestión de incidencias y automatización back-office
4. Metodología y objetivos
5. Desarrollo e implementación
   5.1 Arquitectura del sistema
   5.2 Implementación de las herramientas (Tools)
   5.3 Base de conocimiento (RAG + pólizas)
   5.4 Interfaz de demostración (Streamlit)
6. Evaluación y resultados
   6.1 Dataset y casos de prueba
   6.2 Métricas (KPIs)
   6.3 Simulación de impacto económico (ROI)
7. Conclusiones y trabajo futuro
8. Bibliografía (APA 7.ª edición)
9. Anexos (código, ejemplos de documentos, prompts)
```

---

## Servicios Docker (entorno de desarrollo)

| Servicio | Contenedor | Puerto | Estado |
|---|---|---|---|
| Backend FastAPI | sca-backend | 8000 | ✅ Operativo |
| Frontend Streamlit | sca-frontend | 8501 | ✅ Operativo |
| ChromaDB | sca-chromadb | 8080 | ✅ Operativo |
| MariaDB | sca-mariadb | 3306 | ✅ Operativo |
| Adminer (DB UI) | sca-adminer | 8082 | ✅ Operativo |

Arranque: `docker compose up -d` desde la raíz del repositorio.

---

## Decisiones de diseño clave

- **MVP sobre producto:** prototipo funcional demostrable, no sistema de producción
- **APIs simuladas:** no conecta a sistemas reales → reproducible y seguro para el tribunal
- **Human-in-the-Loop obligatorio** para decisiones de alto importe (`> 5000€`)
- **Chain of Thought visible** en la demo → el tribunal ve el razonamiento, no solo el resultado
- **Simulación económica (ROI)** como diferenciador académico
- **LangGraph** sobre LangChain LCEL por gestión de estado por expediente y HITL nativo
- **aiomysql** como driver async para no bloquear el event loop de FastAPI
- **llama-index excluido del build inicial** → añade ~2 GB; se incorpora en S3

---

## Normativa OBS relevante

- Trabajo **grupal** (4–6 personas) — Art. 9
- Mínimo **3 entregas parciales** evaluadas por rúbrica — Art. 8
- Entrega final en **PDF** via campus virtual — Art. 6
- Defensa oral **virtual**: 25 min exposición + 20 min preguntas tribunal — Art. 15
- **Una única convocatoria** por curso académico — Art. 16
- Citas: **APA 7.ª edición** — Art. 7

### Pesos de evaluación

| Entrega | Peso | Evaluador |
|---|---|---|
| Entrega 1 | 10% | Tutor |
| Entrega 2 | 10% | Tutor |
| Entrega 3 | 10% | Tutor |
| Entrega final — Trabajo escrito | 20% | Tutor |
| Entrega final — Prototipo | 25% | Tribunal |
| Entrega final — Defensa | 25% | Tribunal |

---

## Cronograma

| Fecha | Hito |
|---|---|
| 08/05/2026 | ✅ Entrega 1 entregada |
| 09–15/05/2026 | Feedback tutor Entrega 1 |
| 25/05/2026 | Punto de control E2: infraestructura + Agente A |
| **26/06/2026 23:59** | **Entrega 2 (doc PDF + vídeo ≤4 min)** |
| 15/06/2026 | Code freeze: todos los agentes implementados |
| 22/06/2026 | Demo grabada |
| **30/07/2026 23:59** | **Entrega 3** |
| **25/08/2026 23:59** | **Entrega Final** |
| 08–21/09/2026 | Defensas TFM |

---

## Riesgos identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| VLM con baja precisión en documentos de baja calidad | Media | Alto | Preprocessing + fallback OCR (Tesseract) |
| RAG recupera pólizas incorrectas | Media | Alto | Validación humana para importes > umbral HITL |
| Scope creep (añadir tipos de siniestros) | Alta | Medio | Limitar a 1 caso de uso en el MVP |
| Dataset real no disponible | Alta | Alto | Dataset sintético desde el primer día |
| Latencia alta en demo en vivo | Baja | Medio | Respuestas en caché para la defensa |
| Build lento por dependencias pesadas | Alta | Medio | llama-index excluido; incorporar en S3 |

---

## 🔄 Estado actual y pendientes

### Completado
- [x] Propuesta oficial presentada y entregada
- [x] Confirmación aceptación propuesta por el tutor
- [x] Constitución del grupo de trabajo
- [x] Entrega 1 entregada (08/05/2026)
- [x] Stack tecnológico definitivo decidido
- [x] Repositorio GitHub creado y configurado (tag v0.2.0-start)
- [x] Infraestructura Docker operativa (5 servicios)
- [x] Schema MariaDB: tablas claims, agent_decisions, hitl_feedback
- [x] FastAPI operativo: /health, /api/v1/claims, /api/v1/agents/status
- [x] Agente A — Orquestador LangGraph ReAct implementado
- [x] Mock APIs completas (8 tools con @tool LangChain)
- [x] Frontend Streamlit skeleton operativo
- [x] README.md completo en el repositorio
- [x] .gitignore configurado
- [x] Guía de inicio rápido para el equipo (PDF)

### En curso — Entrega 2 (hasta 26/06/2026)
- [x] Agente B — Validación documental (nodo determinista + mock tool)
- [x] Agente C — Extracción multimodal VLM (mock)
- [x] Agente D — Verificación de cobertura RAG (mock; RAG real en fase posterior)
- [x] Agente E — Resolución autónoma (PAGO / RECHAZO / HITL)
- [x] Agente G — Fraude y cumplimiento (filtro temprano)
- [x] Orquestación LangGraph end-to-end con persistencia de decisiones (20 tests verde)
- [x] CLI de demostración reproducible (`backend/scripts/run_demo.py`)
- [x] Capítulo Arquitectura en la memoria (`docs/memoria/01-arquitectura.md`)
- [x] Catálogo de herramientas en la memoria (`docs/memoria/02-herramientas.md`)
- [x] Manual de usuario (`docs/memoria/03-manual-usuario.md`)
- [ ] Dataset sintético de siniestros (data/synthetic/)
- [ ] Ingesta de pólizas en ChromaDB (scripts/ingest_policies.py)
- [ ] Dashboard Streamlit completo (CoT visible, HITL panel) — no prioritario en E2
- [ ] Fijar targets numéricos de los KPIs
- [ ] Vídeo de demostración (≤ 4 min)

### Pendiente — Entregas 3 y Final
- [ ] Evaluación y métricas (dataset completo)
- [ ] Simulación de costes y ROI
- [ ] Conclusiones y trabajo futuro
- [ ] Bibliografía APA 7.ª completa
- [ ] Consolidación de todas las entregas en PDF final

---

## Referencias bibliográficas (APA 7.ª)

- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). *ReAct: Synergizing reasoning and acting in language models*. arXiv:2210.03629. https://arxiv.org/abs/2210.03629
- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... & Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401
- Anthropic. (2024). *Tool use (function calling) — Claude API documentation*. https://docs.anthropic.com/en/docs/tool-use
- Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., ... & Wen, J. R. (2024). *A survey on large language model based autonomous agents*. Frontiers of Computer Science, 18(6), 186345. https://doi.org/10.1007/s11704-024-40231-1
- Chase, H. (2022). *LangChain* [Software]. https://github.com/langchain-ai/langchain
- LangChain AI. (2024). *LangGraph documentation*. https://langchain-ai.github.io/langgraph/
- Trummer, I. (2023). *From BERT to GPT-4: A survey of large language models*. IEEE Data Engineering Bulletin.
