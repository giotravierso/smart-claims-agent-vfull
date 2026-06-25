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
