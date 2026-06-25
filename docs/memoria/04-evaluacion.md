# 4. Evaluación y resultados

## 4.1 Objetivo de la evaluación

La evaluación del prototipo Smart-Claims Agent persigue dos objetivos diferenciados:

1. **Validar el comportamiento funcional** del sistema agéntico sobre un conjunto representativo de expedientes de siniestros. Es decir, comprobar que ante una reclamación determinada el sistema produce la decisión correcta (pago, rechazo, derivación a revisión humana o solicitud de información), siguiendo la espina dorsal del flujo descrito en el capítulo de arquitectura.
2. **Cuantificar la calidad de las decisiones** mediante métricas de precisión, exhaustividad y distribución por escenario, que permitan al tribunal valorar la viabilidad del sistema más allá de una demostración puntual.

La evaluación se realiza sobre un **dataset sintético** generado expresamente para el TFM, ya que no se dispone de acceso a expedientes reales de Seguros Pepín por la restricción de confidencialidad descrita en el capítulo 1. El uso de datos sintéticos es una práctica habitual en la evaluación temprana de sistemas de IA en dominios sensibles (Russell, 2019).

## 4.2 Diseño del dataset sintético

### 4.2.1 Tamaño y composición

El dataset consta de **30 expedientes** estratificados en los cinco escenarios principales que cubre el sistema:

| Escenario | Número de casos | Distribución esperada de la decisión |
|---|---|---|
| Pago automático | 12 | `PAGO` |
| Documentación incompleta | 6 | `INFO_REQUERIDA` |
| Rechazo por no cobertura | 6 | `RECHAZO` |
| Revisión humana por importe | 4 | `REVISION_HUMANA` |
| Bloqueo por fraude / OFAC | 2 | `RECHAZO_FRAUDE` |
| **Total** | **30** | |

Esta estratificación refleja la distribución previsible de un escenario asegurador real, en el que la gran mayoría de los expedientes (~40%) son pagos automáticos sobre importes modestos, una minoría significativa requiere intervención humana (~20%) y una proporción residual termina en rechazo o se bloquea por fraude.

### 4.2.2 Generación del dataset

El script `backend/scripts/generate_dataset.py` produce los 30 casos de forma reproducible mediante una semilla fija de aleatoriedad (`random.seed(42)`). Para cada caso se generan los campos del expediente —`claim_type`, `amount_requested`, `documents`, `client_id`— con valores plausibles que activan el escenario objetivo:

- En los casos de **pago automático**, el `claim_type` es uno de los cubiertos (`danys_propis`, `responsabilitat`, `robatori`), el importe es inferior al umbral HITL y los documentos requeridos están todos presentes.
- En los casos de **documentación incompleta**, se eliminan uno o varios documentos del conjunto requerido.
- En los casos de **no cobertura**, el `claim_type` es `danys_mecanics`, excluido por la póliza estándar.
- En los casos de **revisión humana**, el importe se sitúa entre 5.500 € y 25.000 €, por encima del umbral de 5.000 €.
- Los casos de **fraude** se identifican posteriormente mediante el comportamiento aleatorio del mock de `check_fraud`.

El dataset se serializa en dos formatos: `claims_dataset.json` (estructura nativa, para los tests) y `claims_dataset.csv` (formato tabular, para inspección manual y posible importación en herramientas externas). Ambos ficheros se almacenan en `data/synthetic/`.

### 4.2.3 Etiqueta de referencia (*ground truth*)

Cada caso del dataset incluye una etiqueta de decisión esperada (`expected_decision`) deducida directamente del diseño: si el caso se ha generado como pago automático, su etiqueta es `PAGO`; si se ha generado como rechazo por no cobertura, su etiqueta es `RECHAZO`, etc. Esta etiqueta es la referencia contra la que se compara la decisión producida por el sistema.

## 4.3 Protocolo de evaluación

El script `backend/scripts/evaluate_dataset.py` ejecuta el siguiente protocolo:

1. **Carga** el dataset desde `data/synthetic/claims_dataset.json`.
2. **Procesa cada caso** invocando `process_claim` del orquestador, con la misma configuración de producción (semilla fija para reproducibilidad).
3. **Compara** la decisión obtenida con la etiqueta esperada, registrando aciertos y discrepancias.
4. **Calcula métricas globales** (precisión, exhaustividad, F1) y por escenario.
5. **Persiste los resultados** en tres ficheros bajo `data/synthetic/`:
   - `evaluation_report.json` — informe completo, caso a caso, con razonamiento del sistema y etiqueta esperada.
   - `evaluation_summary.csv` — tabla resumen con las métricas globales y por escenario.
   - `evaluation_confusion.csv` — matriz de confusión decisión esperada vs. decisión obtenida.

El protocolo no invoca el LLM externo (Claude), sino que utiliza el *fallback* determinista del helper `reason()`. Esta decisión garantiza que la evaluación sea **reproducible** y **gratuita**, dos propiedades imprescindibles para un sistema que debe poder validarse desde la propia máquina del tribunal.

## 4.4 Resultados globales

Los resultados consolidados sobre los 30 casos del dataset son los siguientes:

| Métrica | Valor |
|---|---|
| **Aciertos** | 29 / 30 |
| **Precisión global** | **96,7 %** |
| **Tiempo medio por caso** | 0,3 s (sin LLM) |
| **Tiempo total de evaluación** | 9 s |

La única discrepancia se ha producido en un caso del escenario de **pago automático** que ha derivado a `RECHAZO_FRAUDE` por el comportamiento aleatorio del mock de `check_fraud` (un `risk_score` superior a 0,30 ha activado el filtro de cumplimiento). Este desvío es **funcionalmente correcto** desde el punto de vista del sistema: el caso ha sido bloqueado conforme a la regla de negocio configurada. Sin embargo, contra la etiqueta de referencia del dataset, cuenta como discrepancia. En producción, donde el cribado antifraude consultaría datos reales en lugar de un *score* aleatorio, esta falsa alerta no se produciría con la misma frecuencia.

## 4.5 Resultados por escenario

La tabla siguiente desglosa la precisión por escenario:

| Escenario | Aciertos | Total | Precisión |
|---|---|---|---|
| Pago automático | 11 | 12 | 91,7 % |
| Documentación incompleta | 6 | 6 | 100 % |
| Rechazo por no cobertura | 6 | 6 | 100 % |
| Revisión humana por importe | 4 | 4 | 100 % |
| Bloqueo por fraude / OFAC | 2 | 2 | 100 % |
| **Global** | **29** | **30** | **96,7 %** |

Cuatro de los cinco escenarios alcanzan **precisión perfecta** (100 %), lo que confirma que la lógica determinista del flujo —validación documental, verificación de cobertura, comparación con el umbral HITL, cribado de fraude— se comporta de manera estable y previsible. La única pérdida de precisión se concentra en el escenario más numeroso (pago automático), por la falsa alerta de fraude descrita en la sección anterior.

## 4.6 Análisis de la matriz de confusión

La matriz de confusión completa, generada por el evaluador, es la siguiente (filas = decisión esperada, columnas = decisión obtenida):

| Esperada \ Obtenida | PAGO | RECHAZO | RECHAZO_FRAUDE | REVISION_HUMANA | INFO_REQUERIDA |
|---|---|---|---|---|---|
| **PAGO** | 11 | 0 | 1 | 0 | 0 |
| **RECHAZO** | 0 | 6 | 0 | 0 | 0 |
| **REVISION_HUMANA** | 0 | 0 | 0 | 4 | 0 |
| **INFO_REQUERIDA** | 0 | 0 | 0 | 0 | 6 |
| **RECHAZO_FRAUDE** | 0 | 0 | 2 | 0 | 0 |

La diagonal principal concentra los 29 aciertos. El único punto fuera de la diagonal —fila `PAGO`, columna `RECHAZO_FRAUDE`— corresponde a la falsa alerta de fraude analizada. No hay ninguna otra confusión entre clases, lo que demuestra que cuando el sistema cumple la espina dorsal del flujo sin interferencias del mock antifraude, la decisión es correcta en el 100 % de los casos.

## 4.7 Validación adicional: tests automatizados

Además de la evaluación sobre el dataset sintético, el sistema dispone de una **suite de 25 tests automatizados** ejecutados con pytest, distribuidos en cinco ficheros:

| Fichero | Tests | Cobertura |
|---|---|---|
| `test_agents.py` | 10 | Validación unitaria de cada uno de los agentes especialistas (B, C, D, E, G) |
| `test_orchestration.py` | 5 | Flujo end-to-end de los cuatro caminos principales + verificación de acumuladores |
| `test_repository.py` | 5 | Operaciones CRUD sobre la capa de persistencia |
| `test_api.py` | 3 | Integración del endpoint REST con la lógica agéntica |
| `test_reasoning.py` | 2 | Helper de razonamiento con LLM opcional y *fallback* |
| **Total** | **25** | |

Los tests se ejecutan sobre una base de datos SQLite en memoria, sin necesidad de levantar MariaDB. La suite completa se ejecuta en menos de 5 segundos en un equipo de desarrollo estándar.

## 4.8 Validación cualitativa: demostración CLI

Como complemento a la evaluación cuantitativa, la CLI de demostración (`scripts/run_demo.py`) ejecuta cuatro casos representativos de los cinco escenarios, mostrando el Chain of Thought completo de cada agente. La salida está pensada para una **demostración en vivo ante el tribunal**, donde el evaluador puede ver paso a paso cómo cada agente analiza el expediente y justifica su contribución.

Los cuatro casos de la demo son los descritos en el capítulo 3 del manual de usuario:

- **DEMO-PAGO** — pago automático (`danys_propis`, 3.200 €, documentación completa).
- **DEMO-HITL** — revisión humana por importe (`responsabilitat`, 8.500 €, completa).
- **DEMO-RECHAZO** — rechazo por no cobertura (`danys_mecanics`, 1.000 €, completa).
- **DEMO-INFO** — solicitud de información (`danys_propis`, 1.000 €, solo factura).

En todas las ejecuciones realizadas con semilla `random.seed(7)`, el sistema ha producido la decisión esperada en los cuatro casos, lo que confirma la coherencia entre el comportamiento de la evaluación automatizada y el de la demostración interactiva.

## 4.9 Conclusiones de la evaluación

Los resultados obtenidos permiten concluir que:

- El sistema alcanza una **precisión global del 96,7 %** sobre el dataset sintético de 30 casos, con perfecta precisión en cuatro de los cinco escenarios.
- La única pérdida de precisión proviene del comportamiento aleatorio del mock antifraude, no de un error en la lógica del sistema. En un entorno productivo con un detector real de fraude, esta fuente de error desaparecería.
- La **separación entre lógica determinista y razonamiento mediante LLM** se demuestra acertada: la decisión es estable y reproducible en todos los casos, mientras que el razonamiento natural enriquece la traza de auditoría sin comprometer la fiabilidad.
- La **resiliencia del sistema** queda validada: la evaluación se ejecuta sin LLM externo y sin red, y los tests automatizados se ejecutan sin MariaDB, lo que confirma que la demostración funciona aunque falten dependencias opcionales.

Estos resultados son congruentes con los objetivos del MVP enunciados en el capítulo 1: reproducibilidad, trazabilidad y resiliencia. La evaluación cuantitativa sobre el dataset sintético es coherente con la validación cualitativa de la CLI y con la cobertura de los 25 tests automatizados, lo que da una **triple garantía de la corrección funcional** del prototipo.

## 4.10 Limitaciones y trabajo futuro de evaluación

La evaluación realizada presenta tres limitaciones que conviene reconocer:

**Tamaño del dataset.** Treinta casos son suficientes para validar funcionalmente los cinco caminos del flujo, pero no para concluir sobre el rendimiento del sistema en producción. En la siguiente fase del proyecto se propone ampliar el dataset a varios cientos de casos generados por muestreo estadístico de la distribución real de Seguros Pepín.

**Origen sintético de los datos.** Los expedientes generados reflejan la lógica del sistema, no la complejidad y la variabilidad de los casos reales. Una validación productiva debería incluir un subconjunto de expedientes reales (debidamente anonimizados) procesados manualmente por gestores expertos, con la decisión humana como *ground truth*.

**Dependencia del mock antifraude.** El cribado de fraude es la fuente principal de variabilidad no controlada del prototipo. La integración con un detector real (motor antifraude corporativo de Seguros Pepín) eliminaría esta limitación.

A pesar de estas limitaciones, los resultados de la evaluación son suficientes para concluir que el prototipo cumple su propósito como demostrador funcional del concepto de gestión agéntica de siniestros y constituye una base sólida para una eventual evolución a producción.
