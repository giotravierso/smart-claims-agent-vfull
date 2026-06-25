# Bitácora del proyecto Smart-Claims Agent

Registro cronológico de las decisiones, hitos y problemas resueltos durante el desarrollo del TFM. La bitácora se mantiene como apoyo a la memoria del proyecto y como evidencia de la trayectoria seguida por el equipo técnico.

## Fase 1 — Diseño funcional (marzo–abril 2026)

**Hito 1.1 — Definición del alcance y caso de uso principal.**
Se selecciona el procedimiento SP-PCS-009.1 (reclamaciones por daños propios sobre vehículo asegurado) como prueba de concepto principal del MVP. Se identifican los cinco bloques AS-IS sobre los que debe operar el sistema. Se acuerda con el equipo funcional la división de responsabilidades: secciones 1.x (funcional) y 2.x (técnica) de la memoria.

**Hito 1.2 — Restricciones de contorno.**
Se confirma que el proyecto no dispone de acceso a las APIs reales de Seguros Pepín, S.A. (gestor documental, sistema de pólizas, motor de pagos, listas OFAC). Se decide implementar todas las integraciones externas como *mocks definitivos*, no como mocks temporales, asumiendo que la sustitución por las APIs reales es trabajo de la fase II.

**Hito 1.3 — Marco normativo.**
Se establece que el marco regulatorio aplicable es la Ley 172-13 de Protección de Datos Personales de la República Dominicana, no el RGPD europeo. Se incorpora la mención en todas las referencias normativas de la memoria.

**Hito 1.4 — Convenciones terminológicas.**
Se acuerda usar **expediente** como concepto de negocio y **ticket** como término técnico del sistema (LangGraph en fase I, GLPI en fase II). El código y las decisiones de los agentes referirán siempre a `claim_id` para mantener consistencia con la API.

## Fase 2 — Diseño técnico y arquitectura (mayo 2026)

**Hito 2.1 — Stack tecnológico.**
Se define la pila: Python 3.11 + FastAPI (backend), LangGraph + LangChain (orquestación agéntica), MariaDB 11.3 (persistencia relacional), ChromaDB (vector store), Streamlit (frontend), Docker Compose (despliegue). El modelo LLM seleccionado es Claude Sonnet 4.6 (`claude-sonnet-4-6`) vía API de Anthropic.

**Hito 2.2 — Patrón arquitectónico.**
Se evalúan tres alternativas para la coordinación de los agentes: ReAct libre, cadena dirigida (chain) y patrón Supervisor (Hub-and-Spoke). Se selecciona el **patrón Supervisor** por su trazabilidad lineal, su lógica de flujo centralizada en un único router y su extensibilidad. La decisión queda documentada en el capítulo de arquitectura de la memoria, sección 3.

**Hito 2.3 — Catálogo de agentes.**
Se identifican seis agentes: A (orquestador y supervisor), B (validación documental), C (extracción multimodal), D (verificación de cobertura), E (resolución), G (fraude y cumplimiento). La letra del agente se reserva como referencia interna de la memoria; los ficheros del código adoptan nombres funcionales (`document_validator.py`, etc.) por legibilidad.

**Hito 2.4 — Decisiones HITL.**
Se acuerda activar la revisión humana en dos casos: cuando el agente G marca un cliente como flagged (cribado OFAC/LA-FT) y cuando el importe del siniestro supera un umbral configurable (`HITL_AMOUNT_THRESHOLD`, 5.000 € por defecto). El umbral se exterioriza como variable de entorno para facilitar el ajuste.

## Fase 3 — Implementación inicial (mayo–junio 2026)

**Hito 3.1 — Primer prototipo funcional.**
Implementación inicial del orquestador con LangGraph, los seis agentes en ficheros separados y los siete mocks de herramientas. Despliegue Docker con los cinco servicios (`sca-backend`, `sca-frontend`, `sca-chromadb`, `sca-mariadb`, `sca-adminer`). Validación end-to-end del flujo de pago automático.

**Hito 3.2 — Persistencia relacional.**
Se define el modelo de datos en tres tablas: `claims`, `agent_decisions` y `hitl_feedback`. Se documenta el campo `status` como enum con nueve estados (`open`, `validating`, `extracting`, `checking_policy`, `checking_fraud`, `resolved`, `rejected`, `pending_review`, `closed`). Se resuelve el bug `LookupError` mediante `values_callable=lambda x: [e.value for e in x]` en la definición SQLAlchemy.

**Hito 3.3 — Dataset sintético y evaluación.**
Generación del dataset de 30 casos sintéticos estratificados en los cinco escenarios principales (`scripts/generate_dataset.py`). Implementación del evaluador (`scripts/evaluate_dataset.py`) que produce un informe completo, una matriz de confusión y un resumen de métricas. Primer resultado consolidado: **precisión global del 96,7 %**, con un único desvío explicable por el mock antifraude.

**Hito 3.4 — Dashboard Streamlit.**
Desarrollo de la interfaz web (`frontend/app.py`) con tres componentes: formulario lateral para el envío de reclamaciones, panel central de visualización del Chain of Thought por agente y pestaña de historial con tabla y distribución por estado. Diseño cuidado del estilo visual (paleta sobria, sin iconos decorativos) alineado con la imagen profesional del TFM.

## Fase 4 — Consolidación (junio 2026)

**Hito 4.1 — Refactor a la arquitectura definitiva (solución 2).**
Tras una comparación profunda entre dos ramas paralelas del proyecto, se adopta la arquitectura final que combina lo mejor de ambas:

- Patrón Supervisor (Hub-and-Spoke) puro de la rama solucio1.
- Módulo `state.py` separado con acumuladores `Annotated[list, operator.add]`, de la rama del compañero Gio.
- Helper `reasoning.py` con LLM opcional y *fallback* determinista.
- Repository pattern centralizado en `db/repository.py` para persistencia.
- Estructura de tests con SQLite en memoria (fixtures con `monkeypatch`).
- Dataset y evaluador del 96,7 % recuperados de la rama solucio1.

El resultado se versiona como `v0.6.0-consolidated` en la rama `solucion_final`.

**Hito 4.2 — Normalización del estado final.**
Se identifica un bug en el orquestador: cuando el flujo se cortaba antes del `claim_resolver` (por fraude detectado o documentación incompleta), el campo `status` quedaba en `open` sin reflejar la realidad. Se introduce la función `_normalize_final_state()` que deduce el `status` y la `decision` finales a partir de los resultados parciales acumulados en el estado, garantizando coherencia en la respuesta al cliente.

**Hito 4.3 — Resolución del problema de semilla en el mock antifraude.**
Con la semilla `random.seed(20)` que se usaba inicialmente, el primer valor generado por el mock de `check_fraud` superaba el umbral de 0,30, marcando todos los casos como fraude y cortando el flujo prematuramente. Tras una exploración sistemática, se fija la semilla en `random.seed(7)` (máximo valor 0,231, con margen de seguridad), aplicada en `test_orchestration.py`, `test_api.py` y `scripts/run_demo.py`.

**Hito 4.4 — Validación final.**
La suite de 25 tests automatizados pasa al 100 %. La CLI de demostración ejecuta correctamente los cuatro escenarios principales: `DEMO-PAGO` (resolved, PAGO, 2.900 € pagados), `DEMO-HITL` (pending_review, REVISION_HUMANA), `DEMO-RECHAZO` (rejected, RECHAZO) y `DEMO-INFO` (validating, INFO_REQUERIDA). El sistema queda listo para la entrega.

## Fase 5 — Memoria y entrega (junio 2026)

**Hito 5.1 — Capítulo de arquitectura.**
Se redacta el capítulo 01 de la memoria documentando el patrón Supervisor, la anatomía interna de los agentes (lógica determinista + LLM opcional), el ciclo de ejecución gobernado por `process_claim`, la persistencia best-effort con `try/except`, y la tabla *Mock → Integración real*. Se incorporan referencias APA al *survey* de agentes autónomos (Wang et al., 2024), al patrón ReAct (Yao et al., 2022), al paper de RAG (Lewis et al., 2020) y a la documentación oficial de LangGraph y Anthropic.

**Hito 5.2 — Capítulo de herramientas.**
Capítulo 02 con la descripción detallada de las siete tools del sistema (`validate_documents`, `extract_multimodal`, `check_policy`, `check_fraud`, `approve_payment`, `send_rejection`, `request_more_info`). Se aclara que `log_decision` **no es una tool** sino una funcionalidad transversal del repositorio, evitando la confusión que provenía de versiones anteriores del documento.

**Hito 5.3 — Manual de usuario.**
Capítulo 03 con instrucciones detalladas para reproducir, inspeccionar y validar el sistema. Cubre los tres modos de uso: API REST (con Swagger UI), dashboard Streamlit y CLI de demostración. Incluye ejemplos `curl` para los cinco caminos del flujo y una sección de resolución de problemas frecuentes.

**Hito 5.4 — Capítulo de evaluación.**
Capítulo 04 nuevo, con los resultados completos de la evaluación sobre el dataset sintético: precisión global del 96,7 %, desglose por escenario (4 de 5 con precisión perfecta), matriz de confusión y discusión de limitaciones. Se complementa con la validación cualitativa de la CLI y la cobertura de los 25 tests automatizados.

## Lecciones aprendidas

**Sobre el patrón arquitectónico.** El patrón Supervisor demuestra ser una excelente elección para sistemas multiagente con flujo determinista y necesidad de auditoría. La concentración de la lógica de enrutamiento en un único `supervisor_router` facilita el testing, el mantenimiento y la defensa académica.

**Sobre la dualidad determinista + LLM.** Separar la lógica de negocio crítica (determinista, auditable) del razonamiento natural (LLM opcional, enriquecedor) ha resultado ser una decisión acertada. El sistema funciona en cualquier escenario, y el LLM aporta valor donde realmente añade —en la justificación de las decisiones— sin comprometer su fiabilidad.

**Sobre la persistencia best-effort.** Envolver la persistencia en un `try/except` que tolera fallos de la base de datos ha permitido que la demostración funcione siempre, incluso en entornos donde MariaDB no está disponible. Esta resiliencia ha sido clave para la confianza en la demo del tribunal.

**Sobre la reproducibilidad de los mocks.** Fijar la semilla aleatoria del mock antifraude (`random.seed(7)`) ha sido necesario para que la evaluación sea reproducible. En producción, donde el detector de fraude consulta datos reales, esta dependencia desaparece.

**Sobre la coordinación entre miembros del equipo.** La gestión de dos ramas paralelas del proyecto, cada una con decisiones de diseño diferentes, ha sido el principal reto organizativo. La consolidación final (rama `solucion_final`) ha integrado las mejores prácticas de ambas ramas, evitando la pérdida de trabajo.

## Fase 6 — Motor antifraude y consolidación en main (junio 2026)

**Hito 6.1 — Motor antifraude de 4 detectores.**
Se sustituye el mock aleatorio de `check_fraud` por un motor determinista real (`backend/app/tools/fraud_tools.py`) con cuatro detectores: cribado OFAC mediante *fuzzy matching* (`difflib.SequenceMatcher`, umbral 0,82), detección de importe anómalo por Z-score (umbral 2,0), reclamaciones duplicadas y coherencia documental. El score compuesto produce un veredicto graduado: `BLOCKED` / `HIGH_RISK` (≥0,55) / `MEDIUM_RISK` (≥0,25) / `CLEAR`. Se añaden 15 tests en `test_fraud_tools.py`.

**Hito 6.2 — Actualización del recuento de tests.**
Con el motor antifraude, la suite pasa de 25 a **42 tests** (6 ficheros), todos en verde sobre SQLite en memoria. Se corrige el recuento en el capítulo 04 de la memoria, en `MEMORY.md` y aquí.

**Hito 6.3 — Consolidación oficial en `main`.**
La rama `solucion_final` (tag `v1.0.0-entrega2`) se fusiona a `main` por *fast-forward*; `main` queda como fuente de verdad. Se cierra el PR #1 (rama `feature/prototipo-e2e-entrega2`), ya incorporado en la consolidación.

> **PENDIENTE para el equipo (importante):** el capítulo §4.4–4.6 (evaluación, 96,7 %) y las menciones al *"mock aleatorio de fraude / seed(7)"* (Hitos 4.3–4.4) se midieron **antes** del motor antifraude del Hito 6.1. Como el Agente G ya no usa un score aleatorio sino los 4 detectores deterministas, conviene **re-ejecutar `scripts/evaluate_dataset.py`** y actualizar §4.4–4.6 con los resultados reales del nuevo motor.

## Fase 7 — Clave de IA y despliegue en Streamlit Cloud (junio 2026)

**Hito 7.1 — Configuración de la clave de Anthropic.**
Se añade soporte de `.env` con `load_dotenv()` en los puntos de ejecución (API `main.py` y CLI
`run_demo.py`), **no en los tests** (que siguen corriendo en *fallback*, gratis y deterministas).
La clave real se guarda en `.env` (ignorado por git) y, en el deploy, en los *Secrets* de
Streamlit. Verificado: la clave es válida y el Chain of Thought pasa a generarlo Claude
(`claude-sonnet-4-6`) en lugar del *fallback*.

**Hito 7.2 — Hallazgo: deriva de versiones.**
El entorno de desarrollo real corre versiones mucho más nuevas que las fijadas en
`backend/requirements.txt` (langgraph 1.2.1 vs 0.1.14, langchain-anthropic 1.4.3 vs 0.1.15,
anthropic 0.104.1 vs 0.29.0). Los 42 tests pasan con las nuevas. Para el deploy se fijan las
**versiones que funcionan** (las nuevas) en el `requirements.txt` de la raíz. *(Recomendado:
actualizar también `backend/requirements.txt` para evitar sorpresas en el build Docker.)*

**Hito 7.3 — Dashboard autónomo para Streamlit Cloud.**
Se crea `streamlit_app.py` (raíz): una app **autónoma** que invoca `process_claim`
**in-process**, sin backend FastAPI ni MariaDB (Streamlit Cloud solo ejecuta un proceso).
La persistencia es best-effort (sin BD, el historial vive en sesión). Estética **Salesforce
Lightning** con identidad de marca **Seguros Pepín** (logo real, azul corporativo, acento
naranja); el razonamiento de Claude se renderiza como markdown en una *timeline* de agentes.
Se añade `requirements.txt` (raíz) y `.streamlit/secrets.toml.example`; el `.gitignore` ya
protege `.env` y `.streamlit/secrets.toml`.

**Hito 7.4 — Verificación.**
La app arranca sin errores en modo headless y el camino in-process produce la decisión
correcta con CoT de Claude (caso de prueba: `danys_propis`, 2.500 € → `resolved` / `PAGO`).
Guía de despliegue paso a paso en `docs/DEPLOY-STREAMLIT.md`.

## Fase 8 — Extracción multimodal REAL (Agente C con Claude Vision) (junio 2026)

**Hito 8.1 — De mock a VLM real.**
Hasta ahora el Agente C (extracción multimodal) era un mock: no leía ningún documento real.
Se implementa la extracción **real** con **Claude Vision** (`claude-sonnet-4-6`): el usuario sube
documentos (factura, foto de daños, acta, PDF…) y Claude extrae datos estructurados
(tipo, importe, fecha, emisor, resumen, confianza). Nuevo módulo `backend/app/agents/vision.py`;
el nodo `multimodal_extractor` usa Claude Vision si hay archivos subidos y *fallback* al mock si no
hay archivos o no hay clave. **Justificación:** Claude NO es un sistema de Seguros Pepín, es el LLM
del proyecto, así que esta extracción real **no viola** la regla de "sin APIs externas".

**Hito 8.2 — UI de alimentación del sistema + camino de fraude alcanzable.**
La pregunta "¿cómo subo los documentos para que los agentes los analicen?" se resuelve:
- `streamlit_app.py` añade un **`file_uploader`** (PNG/JPG/WEBP/PDF) en el formulario; los ficheros
  llegan al Agente C, que los analiza con Claude y muestra lo leído en una sección "Extracción
  multimodal real (Claude Vision)".
- Se añade el campo **"Nombre del asegurado"** → el Agente G ya puede comparar contra la lista
  OFAC/ONU (antes el camino de FRAUDE/BLOQUEO no era alcanzable desde el formulario).
- `process_claim` y `ClaimState` aceptan `uploaded_files` y `client_name` (cambios aditivos: sin
  archivos, el flujo es idéntico al anterior → los 42 tests siguen verde).

**Hito 8.3 — Verificación del VLM.**
Verificado con una factura sintética: Claude leyó correctamente importe **3.200,00 €**, fecha
2026-05-10, emisor "Taller Mecánico Martínez" y tipo "factura" (confianza 0,99). La extracción
multimodal es **genuina**, no simulada.

## Fase 9 — RAG REAL de pólizas (Agente D) (junio 2026)

**Hito 9.1 — De tabla de reglas a RAG vectorial.**
El Agente D (cobertura) se anunciaba como "RAG" pero era una **tabla de reglas** (`check_policy`):
ChromaDB estaba levantado pero no se usaba. Se implementa **RAG real**:
- **Pólizas sintéticas** en `data/policies/*.md` (4 docs SP-PCS-009, con frontmatter:
  claim_type, sección, cobertura, límite, franquicia, summary). Claramente marcadas como
  *placeholder*; en producción se alimenta con las pólizas reales de Seguros Pepín.
- **`backend/app/rag/policy_store.py`**: indexa las pólizas en **ChromaDB embebido** (en proceso,
  sin servidor) y recupera por **búsqueda vectorial con filtro de metadato** (`where claim_type`).
- **Agente D** usa la cobertura recuperada por RAG (citando la sección) con **fallback** a
  `check_policy` si el RAG no está disponible. Gated por `SCA_RAG_ENABLED` (la app y Docker lo
  activan; los tests existentes no → siguen usando el mock, sin cambios).

**Hito 9.2 — Embedding ligero + decisión de diseño.**
El embedding por defecto de ChromaDB (ONNX MiniLM) es de **inglés** y recupera mal el español.
En vez de cargar un modelo multilingüe pesado (torch, arriesgado en Streamlit Cloud), se usa
**metadata filtering** por `claim_type`: la búsqueda vectorial rankea la cláusula más relevante
**dentro del tipo de siniestro**. Robusto con corpus pequeño y escalable a varias cláusulas por
tipo. Mantiene el deploy ligero (chromadb + onnxruntime, sin torch).

**Hito 9.3 — Verificación.**
3 tests nuevos (`test_rag.py`): recuperación correcta por tipo (4/4), el Agente D usa RAG y
calcula la cobertura (`danys_propis` 3.200 € → neto 2.900 €, cita SP-PCS-009 §3.2), y fallback al
mock cuando el RAG está desactivado. La UI muestra la sección de póliza recuperada por RAG.
**Esto cierra la mayor brecha del proyecto**: el "RAG" ya no es ficticio.

## Fase 10 — Activar el 4º detector del Agente G (coherencia documental) (junio 2026)

**Hito 10.1 — Diagnóstico.**
El detector de **coherencia documental** del Agente G estaba **muerto** por dos razones: (1) el
orden del flujo (G se ejecutaba antes que C → sin datos extraídos) y (2) la forma de los datos
(`check_document_coherence` esperaba claves planas, pero `extraction_result` las anida bajo
`by_document`). De los "4 detectores", solo 3 estaban activos.

**Hito 10.2 — Arreglo (sin romper el flujo).**
- **Reordenado el flujo** a `A → B → C → G → D → E` (router del supervisor). El Agente G pasa de
  "filtro de entrada" a **gate de cumplimiento tras la recepción documental, antes de la
  resolución** — sigue bloqueando antes de cualquier pago. Solo se reordenó el router; las aristas
  del grafo no cambian → **sin riesgo de bucle**.
- **Aplanada la extracción** (`_flatten_extraction`) para que `check_document_coherence` reciba las
  fechas (compatible con extracción mock y con la real de Claude Vision).
- **Verificación de no-regresión:** la secuencia de `random` se preserva (solo C y E consumen
  random, en el mismo orden relativo) y con datos coherentes el detector da `False` → los tests
  deterministas no cambian. 27 tests sensibles al reorden + 15 de fraude + 3 RAG + 2 nuevos = **47
  verde**.

**Hito 10.3 — Verificación del detector.**
2 tests nuevos (`test_fraud_coherence.py`): con factura previa al siniestro marca incoherencia
(`factura_previa_al_siniestro`); con fechas coherentes no marca. **Los 4 detectores del Agente G
están ahora activos.**

## Fase 11 — Memoria Entrega 2 actualizada + evaluación real (junio 2026)

**Hito 11.1 — Capítulos de memoria reescritos al estado real.**
Se reescriben los 3 capítulos (`01-arquitectura`, `02-herramientas`, `03-manual-usuario`)
reflejando el sistema ACTUAL: flujo `A→B→C→G→D→E`, Agente G con 4 detectores reales, Agente C con
Claude Vision real, Agente D con RAG real (ChromaDB), empresa real + Ley 172-13, 47 tests,
despliegue Streamlit. Verificados contra el código por los redactores.

**Hito 11.3 — Correcciones del peer review.**
Tras una revisión por pares se corrigen: (1) contradicción del orden del Agente G entre documentos
(el orden real es A→B→C→G→D→E; se alinean los 4 capítulos); (2) latencia limpia reportada (~0,25 s
media, sin el timeout de MariaDB); (3) reencuadre del 100 % (lidera "corrección del flujo", caveat
arriba); (4) párrafo explícito "evaluación con LLM apagado"; (5) justificación de la ausencia de los
agentes F y H (fuera del MVP); (6) defensa del auto-rechazo OFAC frente al HITL discrecional;
(7) evaluación del VLM ampliada a 6 documentos (100 % por campo, 17/17); (8,9) nota de localización
de identificadores catalanes y moneda (EUR→DOP en producción); (10) APA unificado (Yao 2022, Russell
2021). Se genera un documento combinado `MEMORIA-Entrega2.md` (portada + 4 capítulos + declaración de
autoría) listo para PDF.

**Hito 11.2 — Evaluación real (capítulo 04).**
El evaluador oficial (`evaluate_dataset.py`) requiere Docker y su mapeo de resultados estaba
desactualizado. Se añade `evaluate_inprocess.py` (in-process, sin Docker, vocabulario actual
PAGO/RECHAZO/REVISION_HUMANA/INFO_REQUERIDA/RECHAZO_FRAUDE) con 32 casos (30 base + 2 OFAC).
**Resultado real: precisión 100 % (32/32)**, matriz de confusión diagonal; OFAC bloquea los 2
casos sancionados (`RECHAZO_FRAUDE`); cobertura por RAG real en el 68,8 % de los casos; TRA 50 %,
HITL 25 %. El motor determinista elimina el falso positivo aleatorio del mock anterior (96,7 % →
100 %). Se reescribe `04-evaluacion.md` con estas métricas.
