# 3. Herramientas del sistema agéntico

## 3.1 Introducción: el rol de las herramientas en un sistema agéntico

En los sistemas de inteligencia artificial basados en agentes, el término *herramienta* (en inglés, *tool*) designa una función de código que el modelo de lenguaje puede invocar de forma autónoma cuando lo considera necesario para resolver una tarea. Esta capacidad, conocida como *function calling* o *tool use*, transforma al modelo de lenguaje de un generador de texto en un agente capaz de actuar sobre el entorno: consultar bases de datos, ejecutar cálculos, enviar notificaciones o registrar decisiones (Anthropic, 2024).

El mecanismo de invocación es el siguiente: al modelo se le proporciona, junto con el mensaje del usuario, una descripción estructurada de cada herramienta disponible —su nombre, los parámetros que acepta y su propósito—. El modelo razona sobre cuál herramienta invocar y con qué argumentos; a continuación, el orquestador ejecuta la función correspondiente y devuelve el resultado al modelo para que continúe su razonamiento. Este ciclo de *razonamiento → acción → observación* es el núcleo del paradigma ReAct (Yao et al., 2023), sobre el que se fundamenta el helper `reason()` empleado en Smart-Claims Agent.

En la implementación concreta de este proyecto, las herramientas se definen mediante el decorador `@tool` de LangChain (Chase, 2022). Este decorador analiza la firma de la función Python y su *docstring* para construir automáticamente el esquema JSON que se expone al modelo. Las herramientas residen en `backend/app/tools/claim_tools.py` y se invocan desde los nodos de los agentes a través del método `.invoke()`.

A diferencia de un enfoque ReAct puro en el que el LLM decide libremente qué herramienta invocar en cada paso, en Smart-Claims Agent **la asignación herramienta–agente es fija y determinista**: cada agente sabe qué herramientas invocará y en qué orden. Esta decisión refuerza la trazabilidad y la reproducibilidad descritas en el capítulo de arquitectura, sin renunciar a la generación de razonamiento natural que aporta el LLM.

**Restricción de entorno.** El prototipo Smart-Claims Agent se ha desarrollado sin acceso a los sistemas reales de Seguros Pepín, S.A. En consecuencia, la totalidad de las herramientas son *mocks definitivos*: implementaciones simuladas que reproducen fielmente las interfaces (firmas, esquemas de entrada y salida) que tendrían sus equivalentes en producción, pero cuya lógica interna genera datos sintéticos o deterministas. Esta decisión de diseño permite demostrar todos los caminos de ejecución del grafo —aprobación, rechazo, solicitud de información adicional, alerta de fraude— de manera reproducible y sin dependencias externas. En cada subsección se documenta explícitamente cómo debería ser la **integración real** en un entorno productivo.

**Persistencia y registro de decisiones.** El registro de decisiones (Chain of Thought de cada agente) **no es una herramienta**, sino una funcionalidad transversal implementada por la capa de repositorio (`app/db/repository.py`). Cada agente acumula su contribución en el campo `decisions_log` del estado compartido durante la ejecución del grafo, y la función `process_claim` persiste todas las decisiones en MariaDB en una única transacción al final del flujo (véase el capítulo de arquitectura, sección 6). Esta separación entre herramientas (acciones sobre el mundo externo) y persistencia (efecto secundario interno gestionado por el repositorio) sigue el principio de separación de responsabilidades.

## 3.2 Tabla resumen de las herramientas

La tabla siguiente ofrece una visión consolidada de las **siete herramientas** que componen el catálogo del sistema, indicando el agente que las invoca, su propósito principal y su estado de implementación.

| # | Herramienta | Agente | Propósito | Estado |
|---|---|---|---|---|
| 1 | `validate_documents` | B – Validación documental | Verificar que los documentos requeridos están presentes y la póliza está activa | Mock |
| 2 | `extract_multimodal` | C – Extracción multimodal (VLM) | Extraer datos estructurados de imágenes, facturas y actas policiales | Mock |
| 3 | `check_policy` | D – Cobertura | Comprobar cobertura, límites y franquicia según el tipo de siniestro | Mock |
| 4 | `check_fraud` | G – Fraude y cumplimiento | Cribar indicios de fraude y cumplimiento normativo (LA/FT, OFAC) | Mock |
| 5 | `approve_payment` | E – Resolución | Emitir la orden de pago al asegurado | Mock |
| 6 | `send_rejection` | E – Resolución | Enviar la comunicación de rechazo justificado al cliente | Mock |
| 7 | `request_more_info` | B – Validación documental | Solicitar documentación faltante al tomador | Mock |

El conjunto se exporta como `AGENT_TOOLS` desde `claim_tools.py`, lo que facilita su registro en LangChain o su inspección unitaria desde los tests.

## 3.3 Descripción detallada de las herramientas

### 3.3.1 `validate_documents`

**Propósito.** Comprueba que el expediente de reclamación contiene la documentación mínima exigida por el procedimiento interno de Seguros Pepín y que la póliza asociada se encuentra en vigor. El conjunto de documentos requeridos depende del tipo de siniestro y se centraliza en la constante `REQUIRED_DOCS_BY_TYPE` del mismo módulo, garantizando que la herramienta y el agente B comparten una única fuente de verdad.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador único de la reclamación |
| `claim_type` | `str` | Tipo de siniestro (`danys_propis`, `responsabilitat`, `robatori`, `danys_mecanics`, `default`) |
| `doc_types` | `list[str]` | Lista de tipos documentales aportados |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `claim_type` | `str` | Tipo de siniestro evaluado |
| `is_valid` | `bool` | Indica si el conjunto documental es suficiente |
| `missing_docs` | `list[str]` | Tipos documentales ausentes |
| `required_docs` | `list[str]` | Lista de documentos requeridos para este tipo |
| `provided_docs` | `list[str]` | Documentos efectivamente aportados |
| `contract_active` | `bool` | Estado de la póliza en la fecha del siniestro |
| `checked_at` | `str` | Marca temporal ISO 8601 de la verificación |

**Agente que la invoca.** Nodo B (Validación documental).

**Mock → Integración real.** En el prototipo, la herramienta simula la verificación comparando la lista de documentos aportados con el conjunto requerido en `REQUIRED_DOCS_BY_TYPE`. En producción, la llamada debería dirigirse al **gestor documental corporativo (ECM)** de Seguros Pepín para confirmar la presencia y la integridad de los ficheros adjuntos, y al **core asegurador** (sistema de gestión de pólizas) para validar que el contrato estaba activo en la fecha del siniestro declarada.

### 3.3.2 `extract_multimodal`

**Propósito.** Extrae información estructurada a partir de ficheros adjuntos de tipo imagen o documento (fotografías de daños, facturas escaneadas, actas policiales). La extracción se fundamenta en un modelo de lenguaje visual (*Vision Language Model*, VLM), capaz de comprender simultáneamente texto e imagen.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador de la reclamación |
| `file_url` | `str` | URL o ruta del fichero a analizar |
| `doc_type` | `str` | Tipo documental (`foto_danys`, `factura`, `acta_policial`, etc.) |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `doc_type` | `str` | Tipo documental procesado |
| `extracted` | `dict` | Datos estructurados extraídos (importe, fecha, descripción de daños, partes, etc.) |
| `confidence` | `float` | Confianza de la extracción en el rango [0, 1] |
| `model` | `str` | Identificador del modelo empleado (`claude-sonnet-4-6 (mock)` en el prototipo) |
| `extracted_at` | `str` | Marca temporal de la extracción |

**Agente que la invoca.** Nodo C (Extracción multimodal). El agente invoca la herramienta una vez por cada documento del expediente y calcula la confianza media; los documentos con confianza inferior a `LOW_CONFIDENCE_THRESHOLD` (0,85) se marcan para revisión.

**Mock → Integración real.** El mock devuelve datos sintéticos plausibles sin procesar ningún fichero real. En un entorno productivo, la herramienta invocaría la **API de Claude con capacidades de visión** (Anthropic, 2024) sobre los adjuntos reales del expediente, enviando la imagen codificada en Base64 junto con un *prompt* estructurado que solicite la extracción de los campos relevantes. Para documentos de baja calidad o resolución insuficiente se contemplaría un *fallback* a OCR clásico mediante Tesseract.

### 3.3.3 `check_policy`

**Propósito.** Determina si el tipo de siniestro declarado está cubierto por la póliza del asegurado, y en caso afirmativo, calcula el importe neto a abonar tras aplicar el límite de cobertura y la franquicia correspondiente.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador de la reclamación |
| `claim_type` | `str` | Tipo de siniestro |
| `amount` | `float` | Importe reclamado en euros |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `claim_type` | `str` | Tipo de siniestro evaluado |
| `amount_requested` | `float` | Importe reclamado |
| `covered` | `bool` | Indica si el siniestro está amparado por la póliza |
| `max_coverage` | `float` | Límite máximo de cobertura aplicable (€) |
| `deductible` | `float` | Franquicia a cargo del asegurado (€) |
| `net_payable` | `float` | Importe neto a satisfacer tras aplicar límites y franquicia (€) |
| `policy_section` | `str` | Cláusula o sección de la póliza que ampara la cobertura (p. ej., `SP-PCS-009 § 3.2`) |

**Agente que la invoca.** Nodo D (Verificación de cobertura).

**Mock → Integración real.** En el prototipo, los valores de cobertura están predefinidos en tablas estáticas según el tipo de siniestro y citan las secciones reales de los procedimientos SP-PCS-009 de Seguros Pepín. La integración real proyectada emplea **Retrieval-Augmented Generation (RAG)** (Lewis et al., 2020) sobre el corpus completo de pólizas indexado en **ChromaDB**, con búsqueda semántica de los fragmentos relevantes para extraer los límites y exclusiones aplicables a cada caso concreto. Esta fase se ha identificado como desarrollo posterior al MVP.

### 3.3.4 Sistema de detección de fraude (cuatro detectores + scoring compuesto)

El cribado antifraude del Agente G no es una única herramienta, sino un sistema modular compuesto por **cuatro detectores deterministas** orquestados por una función de scoring compuesta. Esta arquitectura permite atribuir cada señal de riesgo a una causa concreta y auditable, en lugar de generar un score opaco.

Los cuatro detectores residen en `backend/app/tools/fraud_tools.py`:

| Detector | Función | Salida tipada |
|---|---|---|
| OFAC/ONU | `check_ofac_sanctions(client_name)` — *fuzzy matching* (SequenceMatcher) contra lista mock de sanciones | `OFACResult` |
| Anomalía de importe | `check_amount_anomaly(claim_type, amount)` — Z-score sobre baselines históricos por tipo | `AmountResult` |
| Duplicados | `check_duplicate_claims(client_id, claim_type, history, window_days=90)` — ventana temporal configurable | `DuplicateResult` |
| Coherencia documental | `check_document_coherence(extracted_data)` — comprobaciones temporales entre documentos | `DocCoherenceResult` |

La función `compute_risk_score()` combina los cuatro resultados con pesos calibrados (OFAC 1.0, importe hasta 0.40, duplicado hasta 0.35, incoherencia hasta 0.25) y emite uno de cuatro **veredictos graduados**:

- `BLOCKED` — coincidencia OFAC/ONU confirmada (rechazo automático).
- `HIGH_RISK` — score ≥ 0,55 (HITL obligatorio, supervisor termina el flujo).
- `MEDIUM_RISK` — score ≥ 0,25 (HITL recomendado, decisión humana).
- `CLEAR` — score < 0,25 (el flujo continúa al siguiente agente).

Esta graduación reemplaza el booleano `is_flagged` plano que tenía la versión inicial, permitiendo decisiones más matizadas y una explicabilidad clara: cada veredicto se acompaña de la lista de señales activadas que lo justifican.

**Mock → Integración real.** En el prototipo, la lista de sanciones está hardcodeada con 15 entradas representativas, los baselines de importe son valores estimados y el historial de duplicados está mockeado. En producción, cada detector se conectaría a su fuente real:

| Detector | Fuente real |
|---|---|
| OFAC/ONU | API oficial de OFAC SDN + lista ONU consolidada |
| Anomalía de importe | Cálculo dinámico sobre la tabla `claims` histórica de Seguros Pepín |
| Duplicados | Consulta async a MariaDB con índice por `(client_id, claim_type, created_at)` |
| Coherencia documental | Datos extraídos por el Agente C (capacidades VLM reales) |

### 3.3.5 `approve_payment`

**Propósito.** Emite la orden de pago al asegurado una vez que la reclamación ha sido aprobada. Registra el identificador de transacción y la fecha prevista de abono.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador de la reclamación |
| `amount` | `float` | Importe a abonar (€) |
| `iban` | `str` | Número de cuenta del beneficiario |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `transaction_id` | `str` | Identificador único de la transacción generada |
| `amount` | `float` | Importe abonado (€) |
| `iban_last4` | `str` | Últimos cuatro dígitos del IBAN (trazabilidad sin exponer datos sensibles) |
| `status` | `str` | Estado de la orden (`scheduled`, `processed`, etc.) |
| `scheduled_date` | `str` | Fecha prevista de transferencia (ISO 8601) |

**Agente que la invoca.** Nodo E (Resolución). Se invoca cuando el agente de resolución concluye que la reclamación es válida, está cubierta y el importe está por debajo del umbral HITL.

**Mock → Integración real.** El mock genera un `transaction_id` aleatorio y una fecha calculada a partir del momento de ejecución. En producción, la herramienta se conectaría a la **pasarela de pagos o al core financiero** de Seguros Pepín para emitir una orden de transferencia bancaria real, con los controles de autorización, firma y reconciliación que exige la operativa aseguradora.

### 3.3.6 `send_rejection`

**Propósito.** Comunica al asegurado la resolución denegatoria de su reclamación, incluyendo una justificación clara y los plazos para ejercer su derecho de reclamación, conforme a las obligaciones de información establecidas por la Superintendencia de Seguros de la República Dominicana.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador de la reclamación |
| `reason` | `str` | Motivo del rechazo (texto generado por el agente, normalmente vía LLM) |
| `client_email` | `str` | Dirección de correo electrónico del asegurado |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `email_id` | `str` | Identificador del mensaje enviado |
| `sent_to` | `str` | Dirección de destino |
| `reason_summary` | `str` | Resumen del motivo de rechazo (primeros 200 caracteres) |
| `sent_at` | `str` | Marca temporal del envío (ISO 8601) |

**Agente que la invoca.** Nodo E (Resolución), cuando el agente D ha determinado que el siniestro no está cubierto.

**Mock → Integración real.** El mock registra en consola y devuelve los metadatos del mensaje sin realizar ningún envío real. En producción, la herramienta invocaría el **sistema de notificaciones corporativo o el CRM** de Seguros Pepín para generar y enviar la comunicación mediante el canal acordado con el cliente (correo electrónico, SMS, área de cliente), garantizando el registro de acuse de recibo para fines de cumplimiento.

### 3.3.7 `request_more_info`

**Propósito.** Solicita al asegurado que aporte la documentación o información adicional necesaria para continuar con la tramitación de la reclamación, especificando los campos concretos que faltan y el plazo disponible para su presentación.

**Parámetros de entrada.**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador de la reclamación |
| `missing_fields` | `list[str]` | Lista de campos o documentos ausentes |
| `client_email` | `str` | Dirección de correo electrónico del asegurado |

**Salida.**

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `str` | Identificador del expediente |
| `request_id` | `str` | Identificador de la solicitud de información |
| `fields_requested` | `list[str]` | Campos solicitados (eco de la entrada) |
| `sent_to` | `str` | Dirección de destino |
| `deadline_days` | `int` | Días concedidos al asegurado para responder (10 por defecto en el mock) |
| `sent_at` | `str` | Marca temporal del envío |

**Agente que la invoca.** Nodo B (Validación documental). Se activa cuando `validate_documents` detecta documentos ausentes.

**Mock → Integración real.** En producción, la herramienta interactuaría con el **portal del cliente de Seguros Pepín** o con el proveedor de **correo electrónico transaccional** para generar una comunicación personalizada con enlace directo a la sección de carga de documentos, integrando el seguimiento del estado en el sistema de gestión de expedientes.

## 3.4 Estrategia de simulación: mocks definitivos

La decisión de implementar todas las herramientas como mocks definitivos —en lugar de mocks temporales o integraciones parciales— responde a cuatro criterios fundamentales:

**Reproducibilidad.** Un sistema agéntico presenta comportamiento no determinista a nivel del razonamiento del LLM, pero el entorno de pruebas debe ser reproducible para poder validar los caminos de ejecución del grafo. Al controlar los valores de salida de las herramientas (p. ej., fijar la semilla de aleatoriedad en `check_fraud` o predeterminar qué documentos están presentes en `validate_documents`), es posible verificar de forma sistemática que cada nodo del grafo produce la respuesta esperada ante cada escenario.

**Independencia de sistemas externos.** El desarrollo del prototipo no puede estar condicionado por la disponibilidad, los tiempos de respuesta o los costes de los sistemas reales de Seguros Pepín. Los mocks definitivos eliminan esta dependencia y permiten iterar con rapidez durante la fase de investigación del TFM.

**Fidelidad de la interfaz.** Aunque la lógica interna es simulada, los esquemas de entrada y salida de cada herramienta son idénticos a los que tendría la integración real. Esto garantiza que la sustitución futura de un mock por su equivalente productivo sea un cambio de implementación interna, sin necesidad de modificar el código de los agentes ni la estructura del grafo.

**Cobertura de escenarios.** El conjunto de mocks está diseñado para cubrir todos los caminos de decisión del grafo: reclamación válida y pagada, reclamación rechazada por falta de cobertura, reclamación suspendida por solicitud de documentación, reclamación bloqueada por alerta de fraude, y reclamación derivada a revisión humana por importe. Esta cobertura completa de ramas es esencial para la evaluación del sistema en el contexto académico del TFM.

## 3.5 Tabla consolidada: Mock → Integración real

La siguiente tabla resume el camino de producción previsto para cada herramienta, ofreciendo una visión de conjunto de los sistemas reales que deberían integrarse en una versión productiva de Smart-Claims Agent.

| Herramienta | Integración real proyectada | Sistema / Tecnología |
|---|---|---|
| `validate_documents` | Verificación en gestor documental corporativo (ECM) y core asegurador | ECM de Seguros Pepín + API de pólizas |
| `extract_multimodal` | Extracción mediante VLM sobre adjuntos reales; fallback OCR | Claude Vision API (Anthropic, 2024) + Tesseract |
| `check_policy` | Recuperación semántica sobre condicionados indexados (RAG) | ChromaDB + LangChain (Lewis et al., 2020; Chase, 2022) |
| `check_fraud` | Consulta a listas OFAC/ONU y motor antifraude con scoring LA/FT | API OFAC + motor antifraude corporativo |
| `approve_payment` | Orden de transferencia al core financiero de Seguros Pepín | Pasarela de pagos / módulo financiero del core asegurador |
| `send_rejection` | Comunicación formal por canal preferido del cliente | CRM / sistema de notificaciones corporativo |
| `request_more_info` | Solicitud a través del portal del cliente con enlace de carga | Portal del cliente + email transaccional |

## Bibliografía

Anthropic. (2024). *Tool use (function calling) — Claude API documentation*. https://docs.anthropic.com/en/docs/tool-use

Chase, H. (2022). *LangChain* [Software]. https://github.com/langchain-ai/langchain

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Oguz, B., Riedel, S., & Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv:2005.11401. https://arxiv.org/abs/2005.11401

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). *ReAct: Synergizing reasoning and acting in language models*. International Conference on Learning Representations (ICLR 2023). https://arxiv.org/abs/2210.03629
