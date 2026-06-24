# Arquitectura

## 1. Visión general del sistema

**Smart-Claims Agent** es un sistema agéntico orientado a automatizar la gestión de reclamaciones de siniestros de **Seguros Pepín, S.A.**, desarrollado como Trabajo Fin de Máster del Máster en Machine Learning e Inteligencia Artificial de OBS Business School. El objetivo funcional del sistema es recibir un expediente de siniestro, razonar de forma estructurada sobre él y resolverlo de manera autónoma —pago, rechazo, solicitud de información o derivación a revisión humana— dejando constancia auditable de cada decisión tomada por la cadena de agentes.

El alcance de esta entrega es deliberadamente el de un **MVP (Producto Mínimo Viable) / prototipo demostrable**, no el de un sistema en producción. Esta decisión condiciona toda la arquitectura: prima la claridad, la reproducibilidad y la capacidad de demostración sobre la escalabilidad o la tolerancia a fallos de grado industrial. El sistema está concebido para poder ejecutarse de extremo a extremo y exhibir su razonamiento ante un tribunal académico.

Una **restricción clave y definitiva** atraviesa todo el diseño: el proyecto **no dispone de acceso a las APIs de los sistemas reales de Seguros Pepín** (gestor documental, sistema de pólizas, motor de pagos, listas de sanciones, etc.). En consecuencia, **todas las integraciones externas están simuladas (*mock*) de forma permanente**, no como un estado transitorio en espera de conexión. Cada herramienta del sistema documenta, mediante una nota explícita, cuál sería la integración real que la sustituiría en un despliegue productivo (véase la tabla *Mock → Integración real* en la sección 9). Esta restricción no es un defecto del prototipo, sino una condición de contorno asumida desde el inicio, y la arquitectura se ha diseñado para que la sustitución futura de los *mocks* por integraciones reales sea localizada y de bajo impacto.

En resumen, el sistema persigue tres propiedades rectoras que se repetirán a lo largo del capítulo: **reproducibilidad** (mismo expediente, misma traza), **trazabilidad/auditabilidad** (cada decisión queda registrada y justificada) y **resiliencia de la demostración** (el flujo funciona aunque falten componentes opcionales como la base de datos o la clave de un LLM externo).

## 2. Las cinco capas funcionales y las dos transversales

La arquitectura se organiza en **cinco capas funcionales** apiladas, atravesadas por **dos capas transversales**. La separación por capas facilita el razonamiento sobre responsabilidades y aísla la zona afectada por la restricción de *mocks* (capa 5).

1. **Canales de entrada.** Punto de acceso de los expedientes al sistema. Contempla email, portal web, WhatsApp (simulado) y, como interfaz efectiva del MVP, una **API REST**. Su responsabilidad es normalizar la reclamación entrante a un formato común de expediente.
2. **Orquestación.** Núcleo de coordinación. Contiene el **Agente A (orquestador)**, el grafo de estado de **LangGraph** y la lógica de **Human-in-the-Loop (HITL)**. Decide el orden de invocación de los trabajadores y gestiona las ramas condicionales del flujo.
3. **Agentes especializados.** Los trabajadores que ejecutan las tareas concretas: validación documental (B), extracción multimodal (C), verificación de cobertura (D), resolución (E) y control de fraude/cumplimiento (G).
4. **Datos y conocimiento.** Persistencia y conocimiento corporativo. Incluye **MariaDB** para el registro de expedientes, decisiones y HITL, y **ChromaDB** como base vectorial para la recuperación aumentada (RAG) sobre pólizas, prevista como fase posterior.
5. **Integración simulada.** Conjunto de *mocks* que representan los sistemas externos de Seguros Pepín (documentos, pólizas, pagos, listas OFAC/LA-FT). Es la capa donde se concentra la restricción de no disponer de APIs reales.

Las dos capas transversales atraviesan todas las anteriores:

- **T1 — Seguridad.** Anonimización de datos personales, control de acceso y auditoría de las operaciones.
- **T2 — Observabilidad.** Captura de las trazas de razonamiento (Chain of Thought) y de métricas del flujo, base de la trazabilidad exigida.

El siguiente diagrama ASCII resume la disposición de capas:

```
+=====================================================================+
|                     T1 · SEGURIDAD (anonimización,                  |
|                  control de acceso, auditoría)                      |
+---------------------------------------------------------------------+
|                                                                     |
|   CAPA 1 · CANALES DE ENTRADA                                       |
|   [Email] [Portal web] [WhatsApp (sim.)] [API REST]                 |
|                              |                                      |
|                              v                                      |
|   CAPA 2 · ORQUESTACIÓN                                             |
|   [ Agente A ]──[ LangGraph (grafo de estado) ]──[ HITL ]          |
|                              |                                      |
|                              v                                      |
|   CAPA 3 · AGENTES ESPECIALIZADOS                                   |
|   [G Fraude] [B Docs] [C Extracción VLM] [D Cobertura] [E Resol.]   |
|                              |                                      |
|                              v                                      |
|   CAPA 4 · DATOS Y CONOCIMIENTO                                     |
|   [ MariaDB: claims / decisions / HITL ]  [ ChromaDB: RAG pólizas ] |
|                              |                                      |
|                              v                                      |
|   CAPA 5 · INTEGRACIÓN SIMULADA (mock APIs)                         |
|   [Docs] [Pólizas] [Pagos] [OFAC/LA-FT]  → integración real futura  |
|                                                                     |
+---------------------------------------------------------------------+
|                  T2 · OBSERVABILIDAD (trazas CoT, métricas)         |
+=====================================================================+
```

## 3. El patrón orquestador-trabajadores y su justificación

El sistema implementa un **patrón orquestador-trabajadores** sobre **LangGraph**, materializado como un **grafo de estado** dirigido. Un agente orquestador (A) coordina el flujo y delega tareas específicas en agentes trabajadores especializados (B, C, D, E, G), cada uno responsable de una competencia acotada. Este patrón es una concreción de los sistemas multiagente basados en LLM descritos en la literatura reciente sobre agentes autónomos (Wang et al., 2024), donde la descomposición de una tarea compleja en subtareas asignadas a componentes especializados mejora la fiabilidad frente a un agente monolítico.

La alternativa natural habría sido un **bucle ReAct totalmente libre** (Yao et al., 2022), en el que un único agente alterna razonamiento y acción eligiendo dinámicamente qué herramienta invocar en cada paso. ReAct es un paradigma potente y flexible, pero presenta tres inconvenientes para los objetivos de este TFM:

- **Reproducibilidad.** Un bucle libre puede tomar caminos distintos ante el mismo expediente, lo que dificulta una defensa ante tribunal en la que se espera un comportamiento estable y demostrable.
- **Control del coste de tokens.** Un agente que decide libremente cuántos pasos dar y qué herramientas usar tiene un consumo de tokens difícil de acotar; un grafo con nodos predefinidos hace ese coste predecible.
- **Trazabilidad y auditoría deterministas.** En un dominio asegurador, cada decisión debe poder explicarse y auditarse. Un grafo de estado con transiciones explícitas garantiza que la secuencia de decisiones sea determinista y reconstruible.

Por estas razones se ha optado por **fijar la topología del flujo en un grafo** (LangGraph AI, 2024) en lugar de delegar la planificación en el propio modelo. El razonamiento del estilo ReAct no se descarta: se conserva en el nivel de cada agente como **Chain of Thought** registrado, pero la *orquestación* —qué agente actúa después de cuál— es responsabilidad determinista del grafo, no de una decisión libre del LLM. Se combina así la transparencia del razonamiento agéntico con el control de un flujo de trabajo gobernado.

## 4. Los agentes

El sistema se compone de seis agentes. El orquestador (A) gobierna el flujo; los trabajadores (B, C, D, G) son **nodos deterministas** —funciones puras que invocan su herramienta, razonan sobre el resultado y registran su decisión en el estado—; A y E incorporan además un **helper de razonamiento con LLM opcional**.

| Agente | Rol | Naturaleza |
|--------|-----|-----------|
| **A** | **Orquestador.** Realiza el triaje inicial del expediente y razona el Chain of Thought que guía la entrada al flujo. | LLM opcional + *fallback* determinista |
| **G** | **Fraude / cumplimiento.** Filtro temprano que comprueba listas OFAC y señales de LA-FT (blanqueo de capitales). | Nodo determinista |
| **B** | **Validación documental.** Verifica que el expediente contiene la documentación requerida. | Nodo determinista |
| **C** | **Extracción multimodal.** Extrae datos del expediente mediante un modelo visión-lenguaje (VLM). | Nodo determinista |
| **D** | **Verificación de cobertura.** Comprueba si el siniestro está cubierto por la póliza (apoyado en RAG sobre pólizas). | Nodo determinista |
| **E** | **Resolución autónoma.** Determina la resolución final del expediente (pago, rechazo, etc.). | LLM opcional + *fallback* determinista |

La distinción entre nodos deterministas y agentes con LLM opcional es una decisión deliberada de diseño. Los trabajadores B, C, D y G ejecutan comprobaciones cuyo resultado debe ser estable y verificable, por lo que se implementan como funciones puras sin dependencia de un modelo generativo. En cambio, A y E se benefician de un razonamiento más rico: emplean un **helper que, si está disponible la variable `ANTHROPIC_API_KEY`, enriquece la traza de razonamiento (CoT) invocando a Claude** (modelo `claude-sonnet-4-20250514`) mediante la interfaz de uso de herramientas de la API (Anthropic, 2024). Si la clave no está presente, el helper recurre a un ***fallback* determinista** que produce un razonamiento equivalente sin llamada externa.

Esta dualidad cumple un objetivo concreto: **la demostración funciona siempre**. La dependencia de un servicio externo en una defensa en vivo es un riesgo (caída de red, límite de cuota, latencia), y el *fallback* determinista lo mitiga garantizando que el flujo se complete con o sin conectividad al LLM.

## 5. Flujo de una reclamación

El flujo nominal de extremo a extremo encadena los agentes en el orden:

```
A (triaje) → G (fraude) → B (docs) → C (extracción) → D (cobertura) → E (resolución)
```

Sobre esta espina dorsal se injertan **ramas condicionales** que pueden desviar el expediente antes de llegar a la resolución automática. El diagrama siguiente muestra el flujo completo con sus cinco salidas posibles:

```
              ┌──────────────┐
              │  A · Triaje  │
              └──────┬───────┘
                     v
              ┌──────────────┐   fraude marcado
              │  G · Fraude  │──────────────────────►  [1] REVISIÓN HUMANA (HITL)
              └──────┬───────┘
                     v  ok
              ┌──────────────┐   faltan documentos
              │   B · Docs   │──────────────────────►  [2] SOLICITUD DE INFORMACIÓN (fin)
              └──────┬───────┘
                     v  completo
              ┌──────────────┐
              │ C·Extracción │
              └──────┬───────┘
                     v
              ┌──────────────┐   sin cobertura
              │ D · Cobertura│──────────────────────►  [3] RECHAZO justificado
              └──────┬───────┘
                     v  cobertura OK
              ┌──────────────┐   importe > umbral HITL
              │ E·Resolución │──────────────────────►  [4] REVISIÓN HUMANA (HITL)
              └──────┬───────┘
                     v  importe ≤ umbral
                [5] PAGO automático
```

Las **cinco salidas** del flujo son:

1. **Revisión humana por fraude (HITL temprano).** Si G detecta una coincidencia en listas OFAC o una señal de LA-FT, el expediente se deriva inmediatamente a revisión humana, sin continuar la cadena. Es un filtro temprano de cumplimiento.
2. **Solicitud de información al cliente.** Si B determina que faltan documentos, el flujo termina solicitando al cliente la documentación pendiente. No es un rechazo, sino una pausa a la espera de información.
3. **Rechazo justificado.** Si D concluye que el siniestro no está cubierto por la póliza, el expediente se rechaza con la justificación correspondiente.
4. **Revisión humana por importe.** Si el siniestro tiene cobertura pero el importe supera el umbral HITL (`HITL_AMOUNT_THRESHOLD`, 5000 € por defecto y configurable), E deriva el expediente a revisión humana antes de autorizar el pago.
5. **Pago automático.** Si el siniestro tiene cobertura y el importe es igual o inferior al umbral, E autoriza el pago de forma autónoma. Es el camino de máxima automatización.

Esta combinación de espina dorsal fija y ramas condicionales permite que la mayoría de expedientes simples se resuelvan automáticamente, mientras los casos sensibles (fraude, importes elevados) o incompletos se desvían a la intervención adecuada.

## 6. Gestión de estado y ciclo de ejecución

El estado compartido del grafo se modela mediante `ClaimState`, un `TypedDict` que viaja entre nodos y constituye la única fuente de verdad durante la ejecución. Además de los datos del expediente (identificador, cliente, tipo de siniestro, canal, importes, etc.), `ClaimState` mantiene **dos acumuladores** que crecen a medida que avanza el flujo:

- **`reasoning_trace`** — la traza de Chain of Thought. Cada agente añade su razonamiento, de modo que al final se dispone de la narración completa del proceso de decisión.
- **`decisions_log`** — el registro de decisiones, con **una entrada por agente** (acción tomada, justificación, confianza, necesidad de HITL). Es la base de la auditabilidad.

El ciclo de ejecución se gobierna desde la función `process_claim`, que actúa como punto de entrada de orquestación:

1. Se construye el `ClaimState` inicial a partir del expediente entrante.
2. Se ejecuta el grafo de LangGraph; cada nodo lee el estado, invoca su herramienta, razona y **escribe** su contribución en los acumuladores antes de ceder el control al siguiente nodo según las transiciones del grafo.
3. Tras finalizar el grafo, `process_claim` realiza la **persistencia centralizada**: guarda el expediente y todas sus decisiones en MariaDB.

Un aspecto importante de resiliencia: la persistencia está **envuelta en `try/except`**. Si la base de datos no está disponible, la excepción se captura y el flujo **igualmente devuelve su resultado** (decisión + traza). De este modo, la demostración no depende de que MariaDB esté levantada, lo que refuerza la propiedad de resiliencia descrita en la sección 1.

## 7. Datos y conocimiento

### 7.1. Modelo de datos (MariaDB)

La persistencia relacional se apoya en tres tablas centrales, diseñadas para dar soporte a la trazabilidad y al ciclo HITL:

- **`claims`** — el expediente de reclamación. Campos: `id`, `client_id`, `claim_type`, `channel`, `status`, `amount_requested`, `amount_approved` y marcas temporales.
- **`agent_decisions`** — una fila por decisión de agente, con clave foránea a `claims`. Campos: `id`, `claim_id`, `agent`, `action`, `reasoning`, `confidence`, `hitl_required`, `created_at`. Es la materialización persistente del `decisions_log` y el soporte de la auditoría.
- **`hitl_feedback`** — registro de las anulaciones (*overrides*) humanas, con claves foráneas a `claims` y a `agent_decisions`. Campos: `id`, `claim_id`, `decision_id`, `reviewer`, `original_action`, `final_action`, `override_reason`. Permite contrastar la decisión automática con la final adoptada por un revisor.

El campo `status` se modela como un **enum** con los valores: `open`, `validating`, `extracting`, `checking_policy`, `checking_fraud`, `resolved`, `rejected`, `pending_review` y `closed`. Estos estados reflejan tanto las etapas del flujo (sección 5) como sus salidas terminales.

```
   claims (1) ───< (N) agent_decisions
      |                      |
      |                      |
      └──< (N) hitl_feedback >──┘
        (claim_id)        (decision_id)
```

### 7.2. RAG sobre pólizas (ChromaDB) — fase posterior

La verificación de cobertura (agente D) se beneficiará de la **recuperación aumentada por generación (RAG)** (Lewis et al., 2020) sobre el corpus de pólizas de Seguros Pepín. El enfoque RAG combina la recuperación de fragmentos relevantes desde una base de conocimiento con la generación de respuestas fundamentadas en esos fragmentos, lo que reduce las alucinaciones y permite citar la cláusula concreta que respalda una decisión de cobertura.

En la arquitectura, **ChromaDB** actúa como base vectorial donde se indexarían los textos de las pólizas para su recuperación semántica. Conviene precisar, por exactitud, que esta capacidad está prevista como **fase posterior** del proyecto: en la presente entrega ChromaDB forma parte del despliegue como servicio, pero el RAG completo sobre pólizas no es el foco del MVP. Se documenta aquí porque condiciona el diseño de la capa de datos y la responsabilidad del agente D.

## 8. Human-in-the-Loop (HITL)

El sistema incorpora un mecanismo de **Human-in-the-Loop** que reserva a un revisor humano las decisiones de mayor riesgo, en lugar de automatizarlas ciegamente. El HITL se activa mediante un **doble disparador**:

1. **Disparador por fraude/cumplimiento.** Cuando el agente G marca el expediente (coincidencia OFAC o señal de LA-FT), se deriva a revisión humana de forma temprana, antes de continuar el procesamiento. Es una salvaguarda de cumplimiento normativo.
2. **Disparador por importe.** Cuando el importe del siniestro supera el umbral configurable `HITL_AMOUNT_THRESHOLD` (5000 € por defecto), la resolución (agente E) se deriva a revisión humana aunque la cobertura sea correcta. El umbral, al ser configurable, permite ajustar el grado de automatización a la política de riesgo de la organización.

Las decisiones revisadas se registran en la tabla `hitl_feedback`, que conserva la acción original automática, la acción final adoptada y la razón del *override*. Este registro no solo cierra el bucle de auditoría, sino que constituye una fuente de datos para una eventual mejora futura de los criterios de decisión automáticos.

## 9. Decisiones de diseño clave

La tabla siguiente resume las principales decisiones arquitectónicas y su justificación:

| Decisión | Opción adoptada | Alternativa descartada | Justificación |
|----------|-----------------|------------------------|---------------|
| Motor de orquestación | **LangGraph** (grafo de estado) | LCEL (cadenas LangChain) | Necesidad de flujo con ramas condicionales, estado compartido y transiciones deterministas; LCEL es más adecuado para cadenas lineales (LangGraph AI, 2024). |
| Integraciones externas | **Mocks definitivos** | APIs reales de Seguros Pepín | No hay acceso a las APIs reales; los *mocks* documentan la integración futura y aíslan el cambio en la capa 5. |
| Razonamiento de A y E | **LLM opcional con *fallback* determinista** | Dependencia obligatoria del LLM | Garantiza que la demostración funcione sin conectividad; mitiga el riesgo de fallo en defensa en vivo (Anthropic, 2024). |
| Persistencia | **Centralizada en `process_claim`, con `try/except`** | Persistencia distribuida por nodo | Simplifica el flujo y aporta resiliencia: si no hay BD, el flujo igual devuelve resultado. |
| Acceso a base de datos | **SQLAlchemy 2.0 async + aiomysql** | Acceso síncrono | El backend FastAPI es asíncrono; el acceso no bloqueante a MariaDB evita serializar las peticiones. |

### Tabla *Mock → Integración real*

Por cada integración externa simulada se indica el sistema de Seguros Pepín que la sustituiría en producción:

| Integración simulada (*mock*) | Agente que la usa | Integración real en Seguros Pepín |
|-------------------------------|-------------------|-----------------------------------|
| Listas de sanciones / blanqueo (OFAC, LA-FT) | G (fraude/cumplimiento) | Servicio corporativo de *screening* AML/sanciones (proveedor de listas OFAC/PEP). |
| Repositorio documental del expediente | B (validación documental) | Gestor documental / ECM corporativo de la aseguradora. |
| Extracción de datos de documentos (VLM) | C (extracción multimodal) | Servicio interno de OCR/VLM o plataforma de procesamiento documental. |
| Catálogo y cláusulas de pólizas | D (verificación de cobertura) | Sistema core de pólizas (Policy Administration System) + RAG sobre el corpus real. |
| Autorización y emisión de pagos | E (resolución) | Motor de pagos / tesorería de Seguros Pepín. |
| Canales de notificación al cliente | A / E (solicitud de información, resolución) | Plataformas reales de email, portal de cliente y WhatsApp Business. |

## 10. Despliegue y stack tecnológico

### 10.1. Despliegue (Docker Compose)

El sistema se empaqueta con **Docker Compose** en cinco servicios:

| Servicio | Función | Puerto |
|----------|---------|--------|
| `backend` | API REST (FastAPI + Uvicorn) y orquestación | 8000 |
| `frontend` | Interfaz de demostración (Streamlit) | 8501 |
| `chromadb` | Base vectorial para RAG de pólizas | 8080 |
| `mariadb` | Base de datos relacional | 3306 |
| `adminer` | Administración web de la base de datos | 8082 |

La **API REST** expone los siguientes endpoints principales:

- `POST /api/v1/claims` — procesa un expediente y devuelve la decisión, la traza de Chain of Thought y la información de HITL.
- `GET /api/v1/claims/{id}` — recupera un expediente y sus decisiones.
- `GET /api/v1/agents/status` — estado de los agentes.
- `GET /health` — comprobación de salud del servicio.

El frontend en Streamlit acompaña la demostración, si bien no es prioritario en esta entrega. El flujo puede validarse de extremo a extremo **sin Docker** mediante una CLI de demostración, lo que de nuevo favorece la resiliencia de la prueba.

### 10.2. Stack tecnológico

| Componente | Tecnología |
|-----------|------------|
| Lenguaje | Python 3.11 |
| API REST | FastAPI + Uvicorn |
| Orquestación agéntica | LangGraph + LangChain |
| LLM (razonamiento opcional) | Claude (`claude-sonnet-4-20250514`) vía API de Anthropic |
| Base vectorial (RAG) | ChromaDB *(fase posterior)* |
| Base de datos relacional | MariaDB 11.3 |
| Acceso a datos | SQLAlchemy 2.0 async (driver aiomysql) |
| Frontend demo | Streamlit |
| Empaquetado / despliegue | Docker Compose (5 servicios) |
| Calidad | 20 tests automatizados (pytest) sobre SQLite en memoria |

En cuanto a la **calidad**, el proyecto cuenta con 20 pruebas automatizadas ejecutadas con pytest sobre una base de datos SQLite en memoria, y el flujo se valida de extremo a extremo, sin necesidad de Docker, a través de la CLI de demostración.

## 11. Bibliografía

Anthropic. (2024). *Tool use (function calling) — Claude API documentation*. https://docs.anthropic.com/en/docs/tool-use

Chase, H. (2022). *LangChain* [Software]. https://github.com/langchain-ai/langchain

LangChain AI. (2024). *LangGraph documentation*. https://langchain-ai.github.io/langgraph/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401

Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., … Wen, J. R. (2024). A survey on large language model based autonomous agents. *Frontiers of Computer Science, 18*(6), 186345. https://doi.org/10.1007/s11704-024-40231-1

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). *ReAct: Synergizing reasoning and acting in language models*. arXiv:2210.03629. https://arxiv.org/abs/2210.03629
