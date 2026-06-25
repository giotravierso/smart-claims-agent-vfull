# Arquitectura

## 1. Visión general del sistema

**Smart-Claims Agent** es un sistema agéntico orientado a automatizar el ciclo completo de gestión de una reclamación de siniestro de **Seguros Pepín, S.A.**, aseguradora real con sede en la República Dominicana, desarrollado como Trabajo Fin de Máster del Máster en Machine Learning e Inteligencia Artificial de OBS Business School. El objetivo funcional del sistema es recibir un expediente de siniestro, razonar de forma estructurada sobre él y resolverlo de manera autónoma —pago automático, rechazo, solicitud de información complementaria o derivación a revisión humana— dejando constancia auditable de cada decisión tomada por la cadena de agentes.

El alcance de esta entrega es deliberadamente el de un **MVP (Producto Mínimo Viable) demostrable**, no el de un sistema en producción. Esta decisión condiciona toda la arquitectura: prima la claridad, la reproducibilidad y la capacidad de demostración sobre la escalabilidad o la tolerancia a fallos de grado industrial. El sistema está concebido para ejecutarse de extremo a extremo y exhibir su razonamiento ante un tribunal académico.

Por su naturaleza, el sistema trata datos personales de asegurados (nombre, identificador de cliente, correo electrónico, documentación del siniestro). El marco normativo de referencia no es el RGPD europeo, sino la **Ley 172-13 de Protección de Datos de Carácter Personal de la República Dominicana**, que rige las garantías de tratamiento, conservación y minimización aplicables a Seguros Pepín. Esta condición se refleja en el diseño de la capa de datos (registro auditable, minimización de los datos persistidos) y en las salvaguardas de cumplimiento del Agente G.

Una **restricción clave y definitiva** atraviesa todo el diseño: el proyecto **no dispone de acceso a las APIs de los sistemas reales de Seguros Pepín** (gestor documental, sistema de pólizas, motor de pagos, listas oficiales de sanciones, canales de notificación). En consecuencia, **todas las integraciones con sistemas externos de la aseguradora están simuladas (*mock* / datos sintéticos) de forma permanente**, no como un estado transitorio a la espera de conexión. Esta restricción no es un defecto del prototipo, sino una condición de contorno asumida desde el inicio, y la arquitectura se ha diseñado para que la sustitución futura de los *mocks* por integraciones reales sea localizada y de bajo impacto.

Conviene precisar un matiz importante que recorre todo el capítulo: **el LLM utilizado (Claude) no es un sistema de Seguros Pepín**, sino una capacidad propia del proyecto contratada directamente a su proveedor. Por ello, mientras las integraciones corporativas permanecen simuladas, las **capacidades de inteligencia artificial son reales**: la extracción multimodal con visión por computador, la recuperación aumentada (RAG) sobre el corpus de pólizas y el razonamiento en lenguaje natural se ejecutan de verdad contra modelos y motores reales. La frontera entre "lo simulado" y "lo real" se traza, por tanto, no entre IA y reglas, sino entre *integraciones con terceros sin acceso* (mock) y *capacidades de IA bajo control del proyecto* (reales). La sección 7 formaliza esta distinción.

En resumen, el sistema persigue tres propiedades rectoras que se repetirán a lo largo del capítulo: **reproducibilidad** (mismo expediente, misma traza), **trazabilidad / auditabilidad** (cada decisión queda registrada y justificada) y **resiliencia de la demostración** (el flujo funciona aunque falten componentes opcionales como la base de datos, la clave del LLM o el servicio vectorial).

## 2. El patrón Supervisor (Hub-and-Spoke) y su justificación

El sistema implementa un **patrón Supervisor**, también conocido como **Hub-and-Spoke**, sobre **LangGraph** (LangChain AI, 2024), materializado como un **grafo de estado** dirigido. El **Agente A actúa como supervisor central (hub)** y los agentes especializados (B, C, D, E, G) como radios (*spokes*). La propiedad clave del patrón es que **el supervisor es el único componente que decide el enrutamiento**: cada agente especializado realiza su tarea, escribe su contribución en el estado compartido y devuelve el control al supervisor, que vuelve a evaluar el estado y decide cuál es el siguiente nodo. Los agentes especialistas **no se llaman entre sí** en ningún caso.

Este patrón es una concreción de los sistemas multiagente basados en LLM descritos en la literatura reciente sobre agentes autónomos (Wang et al., 2024), donde la descomposición de una tarea compleja en subtareas asignadas a componentes especializados mejora la fiabilidad frente a un agente monolítico. LangGraph documenta explícitamente esta topología como uno de los patrones canónicos para sistemas multiagente (LangChain AI, 2024).

La alternativa natural habría sido un **bucle ReAct totalmente libre** (Yao et al., 2022), en el que un único agente alterna razonamiento y acción eligiendo dinámicamente qué herramienta invocar en cada paso. ReAct es un paradigma potente y flexible, pero presenta tres inconvenientes para los objetivos de este TFM:

- **Reproducibilidad.** Un bucle libre puede tomar caminos distintos ante el mismo expediente, lo que dificulta una defensa ante tribunal en la que se espera un comportamiento estable y demostrable.
- **Control del coste de tokens.** Un agente que decide libremente cuántos pasos dar y qué herramientas usar tiene un consumo de tokens difícil de acotar; un grafo con nodos predefinidos hace ese coste predecible.
- **Trazabilidad y auditoría deterministas.** En un dominio asegurador, cada decisión debe poder explicarse y auditarse. Un grafo de estado con transiciones explícitas garantiza que la secuencia de decisiones sea determinista y reconstruible.

Por estas razones se ha optado por **fijar la topología del flujo en un grafo con supervisor central** en lugar de delegar la planificación en el propio modelo. El razonamiento del estilo ReAct no se descarta del todo: se conserva en el nivel de cada agente como **Chain of Thought** registrado, pero la *orquestación* —qué agente actúa después de cuál— es responsabilidad determinista del supervisor, no de una decisión libre del LLM. Se combina así la transparencia del razonamiento agéntico (Yao et al., 2022) con el control de un flujo de trabajo gobernado.

El núcleo del supervisor es una función Python pura y determinista, `supervisor_router`, que se invoca como arista condicional (*conditional edge*) del grafo. Decide el siguiente nodo a partir exclusivamente del estado acumulado, evaluando en orden si cada resultado parcial está disponible. Toda la lógica del flujo está concentrada en este único punto, lo que la hace especialmente legible, testeable (basta un test del router) y modificable.

El siguiente diagrama resume la topología Hub-and-Spoke:

```
                        ┌───────────────────────────┐
                        │   A · SUPERVISOR (hub)     │
                        │  supervisor_router(state)  │
                        └─────────────┬─────────────┘
            ┌──────────────┬──────────┼──────────┬──────────────┐
            │              │          │          │              │
            v              v          v          v              v
      ┌───────────┐  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐
      │ B · Docs  │  │ C · Extr.│ │ G ·    │ │ D ·      │ │ E ·       │
      │ validación│  │ multimod.│ │ fraude │ │ cobertura│ │ resolución│
      └─────┬─────┘  └────┬─────┘ └───┬────┘ └────┬─────┘ └─────┬─────┘
            │             │           │           │             │
            └─────────────┴───────────┴───────────┴─────────────┘
                       cada radio DEVUELVE el control
                          al supervisor (nunca a otro radio)
```

## 3. Los seis agentes

El sistema se compone de **seis agentes** organizados en torno al supervisor. Cada agente reside en un fichero separado, siguiendo una convención de nomenclatura dual: el nombre del fichero refleja la responsabilidad funcional, y la letra del agente (A–G) aparece en *docstrings* y *logs* para mantener la trazabilidad con esta memoria.

| Agente | Fichero | Rol | ¿Real o simulado? |
|--------|---------|-----|-------------------|
| **A** | `orchestrator.py` | **Supervisor + triaje.** Punto de entrada del grafo; ejecuta el triaje inicial (razona el CoT) y aloja el `supervisor_router` que enruta a los demás agentes. | Lógica real; CoT con LLM real opcional. |
| **B** | `document_validator.py` | **Validación documental.** Verifica que el expediente contiene los tipos de documento requeridos según el tipo de siniestro; si faltan, solicita información y corta el flujo. | Lógica de validación real sobre el repositorio documental simulado. |
| **C** | `multimodal_extractor.py` | **Extracción multimodal.** Extrae tipo, importe, fecha, emisor, resumen y confianza de los documentos subidos (factura, foto, acta, PDF). | **IA real** con Claude Vision; *fallback* simulado si no hay archivos o clave de API. |
| **G** | `fraud_compliance.py` | **Fraude y cumplimiento.** Motor de cuatro detectores deterministas; emite veredicto graduado y marca el caso para HITL o bloqueo. | **Motor real**; lista de sanciones sintética que simula la SDN. |
| **D** | `coverage_checker.py` | **Verificación de cobertura.** Decide si el siniestro está cubierto recuperando la cláusula relevante de la póliza y citándola (límite, franquicia, neto pagable). | **RAG real** (ChromaDB); pólizas sintéticas; *fallback* determinista. |
| **E** | `claim_resolver.py` | **Resolución autónoma.** Determina la resolución final (PAGO, RECHAZO o REVISIÓN HUMANA) y la ejecuta. | Lógica real; ejecución de pago/rechazo simulada (*mock*). |

A continuación se describe cada agente con el detalle necesario para fijar qué es real y qué es simulado.

**A · Orquestador** (`orchestrator.py`). Es el punto de entrada del grafo. Su nodo `triage_node` enriquece el estado con el razonamiento de bienvenida (sin decidir aún el enrutamiento) y deja el expediente listo para el primer especialista. La función `supervisor_router`, descrita en la sección anterior, constituye el hub determinista del sistema.

**B · Validación documental** (`document_validator.py`). Comprueba que el expediente aporta los tipos de documento exigidos por el tipo de siniestro (por ejemplo, factura y acta para determinados casos). Si detecta documentación incompleta, redacta una solicitud de información al cliente y el supervisor corta el flujo: no es un rechazo, sino una pausa.

**C · Extracción multimodal** (`multimodal_extractor.py`, apoyado en `vision.py`). Es una de las **capacidades de IA reales** del proyecto. Sobre los documentos efectivamente subidos (factura, foto de daños, acta, PDF, informe de taller), invoca a **Claude Vision** (`claude-sonnet-4-6`) y extrae un objeto estructurado con tipo de documento, importe, fecha, emisor, resumen y confianza de la extracción. Como Claude no es un sistema de Seguros Pepín sino el LLM del propio proyecto, esta extracción es real. Si no se aportan archivos o no hay clave de API disponible, el agente recurre a una **extracción simulada** equivalente, de modo que el flujo nunca se interrumpe.

**G · Fraude y cumplimiento** (`fraud_compliance.py`, apoyado en `fraud_tools.py`). Implementa un **motor real de cuatro detectores deterministas**, diseñados para ser auditables señal a señal:

1. **Cribado de sanciones (OFAC / ONU).** Compara el nombre del asegurado contra una lista mediante *fuzzy matching* (`difflib.SequenceMatcher`, umbral de similitud 0,82, con normalización de acentos). La lista es **sintética, de 15 entidades, y simula la lista SDN de la OFAC** y la lista de la ONU; en producción se descargaría periódicamente del servicio oficial.
2. **Anomalía de importe.** Calcula el *Z-score* del importe reclamado frente a una *baseline* por tipo de siniestro (umbral 2,0), marcando también el rebasamiento de un máximo legítimo.
3. **Duplicados recientes.** Detecta reclamaciones del mismo cliente y tipo dentro de una ventana de 90 días.
4. **Coherencia documental.** Verifica la consistencia temporal entre los documentos (fechas de siniestro, reclamación y factura), detectando incoherencias como una fecha de siniestro futura o una reclamación previa al siniestro.

Las señales se combinan en un **score compuesto** que produce un **veredicto graduado**: `BLOCKED` (coincidencia OFAC confirmada → rechazo automático), `HIGH_RISK` (score ≥ 0,55 → HITL obligatorio), `MEDIUM_RISK` (score ≥ 0,25 → HITL recomendado) y `CLEAR` (continúa el flujo). El expediente se marca para HITL o bloqueo cuando el veredicto es `HIGH_RISK` o `BLOCKED`.

**D · Verificación de cobertura** (`coverage_checker.py`, apoyado en `rag/policy_store.py`). Es la segunda **capacidad de IA real**: implementa **RAG (Retrieval-Augmented Generation)** (Lewis et al., 2020) con **ChromaDB embebido** (en proceso, sin servidor externo) sobre un corpus de pólizas (`data/policies/*.md`). El agente recupera la cláusula relevante mediante **búsqueda vectorial filtrada por el metadato `claim_type`** y decide la cobertura citando la sección recuperada (límite de cobertura, franquicia y neto pagable). Las pólizas son **sintéticas** (placeholder del prototipo; en producción se sustituirían por las condiciones reales de Seguros Pepín). Si el RAG no está disponible, el agente cae a una verificación determinista (`check_policy`), de modo que la demostración nunca se rompe.

**E · Resolución** (`claim_resolver.py`). Toma la decisión final del expediente —**PAGO**, **RECHAZO** o **REVISIÓN HUMANA**— y la ejecuta a través de *mocks* (autorización de pago o notificación de rechazo). La ejecución del pago es simulada porque depende del motor de tesorería de la aseguradora, al que no hay acceso.

**LLM opcional (`reasoning.py`).** Transversal a los agentes, el helper `reason()` enriquece el Chain of Thought de cada agente invocando a Claude (`claude-sonnet-4-6`) cuando la variable de entorno `ANTHROPIC_API_KEY` está disponible. En su ausencia, devuelve un *fallback* determinista que produce un razonamiento equivalente sin llamada externa. Esto garantiza una propiedad central: **la demostración funciona siempre**, con o sin conectividad al LLM, mitigando el riesgo de una caída de red o de cuota durante una defensa en vivo.

**Agentes fuera del alcance del MVP.** El catálogo conceptual del proyecto contemplaba además dos agentes que quedan **fuera del alcance de esta entrega** y se reservan para una fase posterior: el **Agente F** (predicción de judicialización del siniestro, basado en aprendizaje automático clásico sobre el histórico de expedientes) y el **Agente H** (asistente legal para expedientes judicializados). Esta entrega implementa el núcleo *end-to-end* del ciclo de gestión (A, B, C, D, E y G); la numeración no correlativa —se pasa de E a G— responde precisamente a esa reserva de las letras F y H para funcionalidades de una fase productiva posterior.

## 4. Flujo de una reclamación

El flujo nominal de extremo a extremo encadena los agentes en el orden:

```
A (triaje) → B (validación docs) → C (extracción) → G (fraude) → D (cobertura) → E (resolución)
```

Las transiciones las decide siempre el supervisor a partir del estado acumulado. Sobre esta espina dorsal se injertan **ramas condicionales** que pueden desviar el expediente antes de la resolución automática. El siguiente diagrama muestra el flujo completo con sus salidas:

```
                      ┌──────────────┐
                      │  A · Triaje  │
                      └──────┬───────┘
                             v
                      ┌──────────────┐   faltan documentos
                      │   B · Docs   │──────────────────────►  [1] SOLICITUD DE INFORMACIÓN (END)
                      └──────┬───────┘
                             v  documentación completa
                      ┌──────────────┐
                      │ C·Extracción │  (Claude Vision real / fallback)
                      └──────┬───────┘
                             v
                      ┌──────────────┐   HIGH_RISK o BLOCKED
                      │  G · Fraude  │──────────────────────►  [2] RECHAZO / HITL por fraude (END)
                      └──────┬───────┘
                             v  CLEAR / MEDIUM_RISK
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

1. **Solicitud de información al cliente.** Si B determina que faltan documentos, el flujo termina con estado `validating` y decisión `INFO_REQUERIDA`. No es un rechazo, sino una pausa a la espera de información.
2. **Rechazo / HITL por fraude.** Si G emite veredicto `HIGH_RISK` o `BLOCKED`, el supervisor termina el flujo antes de la resolución. El expediente queda marcado como `rejected` con causa `RECHAZO_FRAUDE` (o derivado a revisión humana). Es el *gate* de cumplimiento.
3. **Rechazo justificado por no cobertura.** Si D concluye que el siniestro no está cubierto por la póliza, E redacta el rechazo citando la cláusula recuperada y lo notifica al cliente.
4. **Revisión humana por importe.** Si el siniestro tiene cobertura pero el importe supera el umbral HITL (`HITL_AMOUNT_THRESHOLD`, 5.000 € por defecto y configurable), E deriva el expediente a revisión humana antes de autorizar el pago.
5. **Pago automático.** Si el siniestro tiene cobertura y el importe es igual o inferior al umbral, E autoriza el pago de forma autónoma. Es el camino de máxima automatización.

### 4.1. Por qué el cribado de fraude (G) se ejecuta tras la recepción documental

Una decisión de diseño relevante es la **posición del Agente G en el flujo**. Aunque conceptualmente el cribado de fraude actúa como un *gate* de cumplimiento previo a la resolución y al pago, el router lo ejecuta **después** de la validación documental (B) y la extracción multimodal (C), y no como primer filtro de entrada. La razón es funcional: dos de los cuatro detectores de G —en particular el de **coherencia documental** y, en parte, el de **anomalía de importe**— necesitan los **datos efectivamente extraídos** de los documentos (fechas de siniestro, factura y reclamación; importe consolidado) para poder operar. Situar G antes de la extracción lo privaría de esa información y degradaría su capacidad de detección.

De este modo, G se beneficia de los datos ya extraídos por C **sin renunciar** a su papel de salvaguarda: sigue actuando como barrera de cumplimiento **antes** de que se verifique la cobertura (D) y, sobre todo, **antes** de cualquier resolución o pago (E). Se concilia así la necesidad de datos del detector con la garantía de que ningún expediente fraudulento llega a pagarse.

## 5. Gestión de estado y ciclo de ejecución

El estado compartido del grafo se modela mediante `ClaimState`, un `TypedDict` que viaja entre nodos y constituye la única fuente de verdad durante la ejecución. LangGraph lo propaga automáticamente: cada agente lee lo que necesita y devuelve una actualización parcial que se fusiona con el estado existente. Sus campos se agrupan en cuatro bloques:

- **Identidad del expediente:** `claim_id`, `client_id`, `client_name`, `client_email`. El nombre del asegurado es necesario para el cribado OFAC de G.
- **Datos de entrada:** `claim_type`, `amount_requested`, `channel`, `documents` y `uploaded_files` (los archivos binarios reales para el análisis multimodal de C).
- **Resultados parciales** de cada agente: `validation_result` (B), `extraction_result` (C), `fraud_result` (G), `coverage_result` (D) y `resolution` (E).
- **Acumuladores y control de flujo:** `reasoning_trace`, `decisions_log`, `status`, `decision`, `hitl_required`, `terminate` y `termination_reason`.

Los **dos acumuladores** crecen a medida que avanza el flujo y son la base de la trazabilidad:

- **`reasoning_trace`** — la traza de Chain of Thought. Cada agente añade su razonamiento, de modo que al final se dispone de la narración completa del proceso de decisión.
- **`decisions_log`** — el registro de decisiones, con **una entrada por agente** (agente, acción, justificación, confianza, necesidad de HITL). Es la materialización auditable del proceso.

Ambos campos se declaran como `Annotated[list, operator.add]`, lo que indica a LangGraph que las contribuciones de los distintos nodos deben **acumularse** en lugar de sobrescribirse. Es un detalle técnico clave: permite que cada agente añada su entrada sin pisar las anteriores, preservando el Chain of Thought completo.

El ciclo de ejecución se gobierna desde la función `process_claim`, que actúa como punto de entrada de orquestación:

1. Se construye el `ClaimState` inicial a partir del expediente entrante.
2. Se ejecuta el grafo de LangGraph mediante `ainvoke`; cada nodo lee el estado, invoca su herramienta, razona y **escribe** su contribución en los acumuladores antes de ceder el control al supervisor.
3. Tras finalizar el grafo, la función auxiliar `_normalize_final_state` deduce el `status` y la `decision` finales en los casos en que el flujo se ha cortado sin pasar por el resolver (por ejemplo, fraude marcado por G o documentos incompletos detectados por B). Esto garantiza que la respuesta al cliente sea siempre coherente.
4. Finalmente, `process_claim` realiza la **persistencia centralizada** de todas las decisiones en MariaDB, en una única transacción.

Un aspecto esencial de resiliencia: la persistencia está **envuelta en `try/except`**. Si la base de datos no está disponible (por ejemplo, en la CLI de demostración sin MariaDB), la excepción se captura y el flujo **igualmente devuelve su resultado** (decisión + traza). Se trata de una persistencia *best-effort*: la demostración no depende de que MariaDB esté levantada, lo que refuerza la propiedad de resiliencia descrita en la sección 1.

## 6. Datos y conocimiento

### 6.1. Modelo de datos (MariaDB)

La persistencia relacional se apoya en **MariaDB** mediante **SQLAlchemy 2.0 asíncrono** (driver `aiomysql`) y un patrón repositorio. El esquema se compone de tres tablas centrales, diseñadas para dar soporte a la trazabilidad y al ciclo HITL:

- **`claims`** — el expediente de reclamación. Recoge identidad del cliente, tipo de siniestro, canal, estado, importe solicitado e importe aprobado, con marcas temporales.
- **`agent_decisions`** — una fila por decisión de agente, con clave foránea a `claims`. Registra el agente, la acción, el razonamiento (CoT), la confianza, si requirió HITL y el momento. Es la materialización persistente del `decisions_log` y el soporte de la auditoría.
- **`hitl_feedback`** — registro de las anulaciones (*overrides*) humanas, con claves foráneas a `claims` y a `agent_decisions`. Conserva el revisor, la acción original automática, la acción final adoptada y la razón del *override*, permitiendo contrastar la decisión automática con la humana.

El campo `status` se modela como un **enum** con los valores `open`, `validating`, `extracting`, `checking_policy`, `checking_fraud`, `resolved`, `rejected`, `pending_review` y `closed`. Estos estados reflejan tanto las etapas del flujo (sección 4) como sus salidas terminales.

```
   claims (1) ───< (N) agent_decisions
      |                      |
      |                      |
      └──< (N) hitl_feedback >──┘
        (claim_id)        (decision_id)
```

### 6.2. RAG sobre pólizas (ChromaDB)

La verificación de cobertura (Agente D) se apoya en **recuperación aumentada por generación (RAG)** (Lewis et al., 2020) sobre el corpus de pólizas. El enfoque RAG combina la recuperación de fragmentos relevantes desde una base de conocimiento con la generación de respuestas fundamentadas en esos fragmentos, lo que reduce las alucinaciones y permite **citar la cláusula concreta** que respalda una decisión de cobertura.

En esta entrega el RAG está **operativo**: **ChromaDB embebido** (en proceso) indexa los documentos de póliza (`data/policies/*.md`), cada uno con un *frontmatter* de metadatos (tipo de siniestro, sección, cobertura, límite, franquicia). El Agente D recupera la cláusula más relevante mediante **búsqueda vectorial con filtrado por el metadato `claim_type`**, robusta con corpus pequeño y escalable a varias cláusulas por tipo. Las pólizas son **sintéticas** (placeholder del prototipo), pendientes de sustitución por las condiciones reales de Seguros Pepín en un despliegue productivo.

## 7. Capacidades de IA reales frente a integraciones simuladas

La frontera entre lo real y lo simulado en este proyecto no separa "inteligencia artificial" de "reglas", sino **integraciones con terceros sin acceso** (necesariamente simuladas) de **capacidades de IA bajo control del proyecto** (reales). Esta sección formaliza ambas listas.

### 7.1. Integraciones externas simuladas (tabla *Mock → Integración real*)

Por cada integración con un sistema de Seguros Pepín al que no hay acceso, se indica el componente que la sustituiría en producción:

| Integración simulada (*mock*) | Agente que la usa | Integración real en Seguros Pepín |
|-------------------------------|-------------------|-----------------------------------|
| Listas oficiales de sanciones (OFAC SDN / ONU) | G (fraude / cumplimiento) | Servicio corporativo de *screening* AML / sanciones con suscripción a las listas oficiales actualizadas. |
| Repositorio documental del expediente | B (validación documental) | Gestor documental / ECM corporativo de la aseguradora. |
| Catálogo y cláusulas de pólizas | D (verificación de cobertura) | Sistema *core* de pólizas (Policy Administration System), indexado por el RAG real. |
| Autorización y emisión de pagos | E (resolución) | Motor de pagos / tesorería de Seguros Pepín. |
| Canales de notificación al cliente | A / E (solicitud de información, resolución) | Plataformas reales de email, portal de cliente y WhatsApp Business. |

### 7.2. Capacidades de IA reales

Frente a lo anterior, las siguientes capacidades se ejecutan de verdad, porque dependen de modelos y motores bajo control del proyecto (no de Seguros Pepín):

| Capacidad real | Agente | Tecnología | Mecanismo de resiliencia |
|----------------|--------|------------|--------------------------|
| Extracción multimodal (visión) | C | Claude Vision (`claude-sonnet-4-6`) | *Fallback* a extracción simulada si no hay archivos o clave de API. |
| RAG sobre pólizas | D | ChromaDB embebido + búsqueda vectorial con filtro de metadato | *Fallback* determinista (`check_policy`) si el RAG no está disponible. |
| Motor de 4 detectores de fraude | G | Algoritmos deterministas (fuzzy matching, Z-score, ventana temporal, coherencia de fechas) | Determinista por diseño; no depende de servicios externos. |
| Razonamiento en lenguaje natural (CoT) | A–E, G | Claude (`claude-sonnet-4-6`) vía `reason()` | *Fallback* determinista equivalente si no hay clave de API. |

La combinación de capacidades reales y *fallbacks* deterministas hace que el sistema sea, a la vez, **demostrable de verdad** (las capacidades de IA funcionan) y **resiliente** (el flujo se completa aunque falle cualquier componente opcional).

## 8. Human-in-the-Loop (HITL)

El sistema incorpora un mecanismo de **Human-in-the-Loop** que reserva a un revisor humano las decisiones de mayor riesgo, en lugar de automatizarlas ciegamente. El HITL se activa mediante un **doble disparador**:

1. **Disparador por fraude / cumplimiento.** Cuando el Agente G emite veredicto `HIGH_RISK` o `BLOCKED`, el expediente se marca para revisión humana (o bloqueo) antes de continuar hacia la resolución. Es una salvaguarda de cumplimiento normativo.
2. **Disparador por importe.** Cuando el importe del siniestro supera el umbral configurable `HITL_AMOUNT_THRESHOLD` (5.000 € por defecto), la resolución (Agente E) se deriva a revisión humana aunque la cobertura sea correcta. Al ser configurable, el umbral permite ajustar el grado de automatización a la política de riesgo de la organización.

En ambos casos el expediente queda en estado `pending_review`. Las decisiones revisadas se registran en la tabla `hitl_feedback`, que conserva la acción original automática, la acción final adoptada y la razón del *override*. Este registro no solo cierra el bucle de auditoría, sino que constituye una fuente de datos para una eventual mejora futura de los criterios de decisión automáticos.

Conviene precisar la diferencia de naturaleza entre los dos disparadores. La **revisión por importe** responde a una decisión de política discrecional: la organización elige a partir de qué cuantía prefiere supervisión humana, y ese umbral es configurable. La **coincidencia con listas de sanciones OFAC/ONU**, en cambio, constituye una obligación legal vinculante sin margen de discrecionalidad; por ello el sistema la trata como bloqueo automático (`RECHAZO_FRAUDE`) en lugar de derivarla a revisión. Como refinamiento, dicho bloqueo podría redirigirse a un oficial de cumplimiento (HITL de cumplimiento) para su confirmación formal, manteniendo el principio de intervención humana en los casos sensibles y creando además una traza documentada del proceso.

## 9. Despliegue y stack tecnológico

### 9.1. Despliegue

El sistema admite **dos modos de despliegue** complementarios.

**(1) Docker Compose — arquitectura completa.** Empaqueta el sistema en **cinco servicios**, con base de datos y servicios reales:

| Servicio | Función | Puerto |
|----------|---------|--------|
| `backend` | API REST (FastAPI + Uvicorn) y orquestación de agentes | 8000 |
| `frontend` | Interfaz de demostración (Streamlit) | 8501 |
| `chromadb` | Base vectorial para el RAG de pólizas | 8080 |
| `mariadb` | Base de datos relacional | 3306 |
| `adminer` | Administración web de la base de datos | 8082 |

**(2) App Streamlit autónoma — demo en vivo.** El fichero `streamlit_app.py` es una aplicación autónoma desplegable en **Streamlit Community Cloud** que ejecuta los agentes **en proceso**, sin backend ni MariaDB. Pensada para la demostración en vivo, aprovecha la persistencia *best-effort* (sección 5) y los *fallbacks* deterministas (sección 7) para funcionar sin la infraestructura completa.

### 9.2. Stack tecnológico

| Componente | Tecnología |
|-----------|------------|
| Lenguaje | Python 3.11 |
| API REST | FastAPI + Uvicorn |
| Orquestación agéntica | LangGraph + LangChain (Chase, 2022; LangChain AI, 2024) |
| LLM (visión y razonamiento) | Claude Sonnet 4.6 (`claude-sonnet-4-6`) vía API de Anthropic (Anthropic, 2024) |
| Base vectorial (RAG) | ChromaDB (embebido en la app autónoma; servicio en Docker) |
| Base de datos relacional | MariaDB 11.3 |
| Acceso a datos | SQLAlchemy 2.0 async (driver aiomysql); SQLite en memoria para tests |
| Frontend / demo | Streamlit |
| Empaquetado / despliegue | Docker Compose (5 servicios) + Streamlit Community Cloud |
| Calidad | 47 tests automatizados (pytest) sobre SQLite en memoria, sin dependencia de MariaDB |

En cuanto a la **calidad**, el proyecto cuenta con **47 pruebas automatizadas** ejecutadas con pytest sobre una base de datos SQLite en memoria, que cubren los agentes individuales, el flujo de orquestación completo, los detectores de fraude (incluida la coherencia documental), el RAG, la capa de repositorio, el helper de razonamiento y los endpoints de la API REST. Al no depender de MariaDB, la suite es reproducible en cualquier entorno.

**Nota sobre localización.** Los identificadores de tipo de siniestro (`danys_propis`, `responsabilitat`, `robatori`, `danys_mecanics`) y la moneda de referencia (euros) se heredan del andamiaje inicial del prototipo. En una implantación real para Seguros Pepín (República Dominicana) se localizarían a castellano dominicano y a pesos dominicanos (DOP / RD$); las etiquetas visibles para el usuario ya se presentan en castellano. Esta adaptación afectaría únicamente a los valores de las enumeraciones internas y a la capa de presentación, sin alterar la lógica de los agentes.

## 10. Bibliografía

Anthropic. (2024). *Tool use (function calling) — Claude API documentation*. https://docs.anthropic.com/en/docs/tool-use

Chase, H. (2022). *LangChain* [Software]. https://github.com/langchain-ai/langchain

LangChain AI. (2024). *LangGraph documentation: Multi-agent supervisor pattern*. https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401

Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., … Wen, J. R. (2024). A survey on large language model based autonomous agents. *Frontiers of Computer Science, 18*(6), 186345. https://doi.org/10.1007/s11704-024-40231-1

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). *ReAct: Synergizing reasoning and acting in language models*. arXiv:2210.03629. https://arxiv.org/abs/2210.03629
