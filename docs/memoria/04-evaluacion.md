# 4. Evaluación y resultados

## 4.1 Objetivo de la evaluación

La evaluación del prototipo Smart-Claims Agent persigue dos objetivos:

1. **Validar el comportamiento funcional** del sistema agéntico sobre un conjunto
   representativo de expedientes, comprobando que ante cada reclamación produce la
   decisión correcta (pago automático, rechazo, revisión humana, solicitud de
   información o bloqueo por fraude) siguiendo el flujo descrito en el capítulo de
   arquitectura.
2. **Verificar las capacidades reales de IA** incorporadas al sistema: el motor
   antifraude de cuatro detectores (incluida la verificación OFAC), la recuperación
   aumentada (RAG) de cobertura y la lógica de resolución.

La evaluación se realiza sobre un **dataset sintético** generado expresamente, ya que
no se dispone de acceso a expedientes reales de Seguros Pepín por la restricción de
confidencialidad descrita en el capítulo 1. El uso de datos sintéticos es una práctica
habitual en la validación temprana de sistemas de IA en dominios sensibles (Russell &
Norvig, 2021).

## 4.2 Diseño del dataset sintético

### 4.2.1 Tamaño y composición

El dataset consta de **32 expedientes** estratificados en seis escenarios que cubren las
cinco salidas del flujo más una demostración explícita del cribado OFAC:

| Escenario | Casos | Decisión esperada |
|---|---|---|
| Pago automático | 10 | `PAGO` |
| Revisión humana por importe (HITL) | 6 | `REVISION_HUMANA` |
| Rechazo por no cobertura | 4 | `RECHAZO` |
| Documentación incompleta | 8 | `INFO_REQUERIDA` |
| Bloqueo por sanción OFAC | 2 | `RECHAZO_FRAUDE` |
| Importe inusual (potencial fraude) | 2 | `REVISION_HUMANA` |
| **Total** | **32** | |

La estratificación refleja la distribución previsible de un escenario asegurador real,
donde la mayoría de expedientes son pagos automáticos sobre importes modestos y una
proporción menor requiere intervención humana, rechazo o bloqueo.

### 4.2.2 Generación

Los casos se construyen de forma reproducible (semilla fija de aleatoriedad). Para cada
caso se fijan `claim_type`, `amount_requested`, `documents` y `client_name` con valores
que activan el escenario objetivo:

- **Pago automático:** tipo cubierto (`danys_propis`, `responsabilitat`, `robatori`),
  importe por debajo del umbral HITL (5.000 €) y documentación completa.
- **Revisión humana:** importe entre 6.500 € y 40.000 € (por encima del umbral).
- **No cobertura:** tipo `danys_mecanics`, excluido por la póliza.
- **Documentación incompleta:** se elimina uno de los documentos requeridos.
- **Bloqueo OFAC:** se emplea como nombre del asegurado una entidad de la lista de
  sanciones sintética (p. ej. *Viktor Nikolaev Kozlov*, *Dmitri Volkov*).
- **Importe inusual:** importes anómalos (9.999,99 € y 7.777,77 €) con cliente sospechoso.

Las pólizas, la lista OFAC y los baselines de importe son **sintéticos** (placeholder
del prototipo); en producción se alimentan con los datos reales de Seguros Pepín.

## 4.3 Protocolo de evaluación

La evaluación se ejecuta con el script `backend/scripts/evaluate_inprocess.py`, que
invoca la función `process_claim` **en proceso** (sin necesidad del backend REST ni de
MariaDB) sobre los 32 casos y compara la decisión obtenida con la esperada. Se eligió la
evaluación en proceso porque:

1. No requiere levantar la infraestructura Docker completa, facilitando la
   reproducibilidad desde cualquier máquina.
2. Emplea el vocabulario de decisiones actual del sistema (`PAGO`, `RECHAZO`,
   `REVISION_HUMANA`, `INFO_REQUERIDA`, `RECHAZO_FRAUDE`).

> El proyecto conserva además el evaluador `evaluate_dataset.py`, que ejecuta el mismo
> protocolo contra el endpoint REST cuando el sistema corre en Docker.

El protocolo se ejecuta con el **RAG real activo** (`SCA_RAG_ENABLED=1`) y **sin LLM
externo** (se usa el *fallback* determinista del razonamiento), de modo que la
evaluación es **reproducible** y **gratuita** —dos propiedades imprescindibles para que
pueda validarse desde la propia máquina del tribunal—. La persistencia en MariaDB es
*best-effort*: en el entorno de evaluación, sin base de datos, se omite con un aviso y el
flujo continúa.

## 4.4 Resultados globales

| Métrica | Valor |
|---|---|
| **Casos correctos** | 32 / 32 |
| **Precisión global** | **100 %** |
| **Tasa de Resolución Autónoma (TRA)** | 50,0 % (casos resueltos/rechazados sin HITL) |
| **Tasa de HITL** | 25,0 % |
| **Cobertura decidida por RAG real** | 68,8 % de los casos (los que alcanzan al Agente D) |

El sistema clasificó correctamente los 32 expedientes. La **TRA del 50 %** corresponde a
los pagos automáticos (10) y rechazos (4 por no cobertura + 2 por OFAC) que se resuelven
sin intervención humana; el **25 % de HITL** corresponde a las 8 derivaciones a revisión
humana por importe. La **cobertura se decidió por RAG** en el 68,8 % de los casos: el
resto no llega al Agente D porque se corta antes (documentación incompleta → solicitud de
información; sanción OFAC → bloqueo).

> Nota sobre tiempos: la latencia media observada está dominada por el *timeout* de
> conexión a MariaDB en el entorno de evaluación (sin BD), debido a la persistencia
> *best-effort*. El procesamiento agéntico en sí es de fracciones de segundo por caso.

## 4.5 Resultados por escenario

| Escenario | Aciertos | Total | Precisión |
|---|---|---|---|
| Pago automático | 10 | 10 | 100 % |
| Revisión humana por importe | 6 | 6 | 100 % |
| Rechazo por no cobertura | 4 | 4 | 100 % |
| Documentación incompleta | 8 | 8 | 100 % |
| Bloqueo por sanción OFAC | 2 | 2 | 100 % |
| Importe inusual (potencial fraude) | 2 | 2 | 100 % |
| **Global** | **32** | **32** | **100 %** |

## 4.6 Matriz de confusión

Filas = escenario esperado, columnas = decisión obtenida. La diagonal concentra los 32
aciertos; no hay ninguna confusión entre clases.

| Esperado \ Obtenido | PAGO | REVISION_HUMANA | RECHAZO | INFO_REQUERIDA | RECHAZO_FRAUDE |
|---|---|---|---|---|---|
| **Pago automático** | 10 | 0 | 0 | 0 | 0 |
| **Revisión por importe** | 0 | 6 | 0 | 0 | 0 |
| **No cobertura** | 0 | 0 | 4 | 0 | 0 |
| **Doc. incompleta** | 0 | 0 | 0 | 8 | 0 |
| **Sanción OFAC** | 0 | 0 | 0 | 0 | 2 |
| **Importe inusual** | 0 | 2 | 0 | 0 | 0 |

## 4.7 Validación del motor antifraude (Agente G)

La evaluación confirma el funcionamiento de los detectores reales:

- **Verificación OFAC/ONU:** los 2 expedientes con nombre sancionado se marcaron con
  veredicto **`BLOCKED`** y se resolvieron como `RECHAZO_FRAUDE`, demostrando que el
  *fuzzy matching* (umbral 0,82) contra la lista de sanciones funciona de extremo a extremo.
- **Anomalía de importe (Z-score):** varios casos de importe elevado obtuvieron veredicto
  `MEDIUM_RISK` (el detector se activa, pero el score no alcanza el umbral de bloqueo de
  0,55). Es el comportamiento correcto: el sistema señala la anomalía sin bloquear, y la
  derivación a revisión humana la produce el umbral de importe en el Agente E.
- **Coherencia documental:** verificado adicionalmente con pruebas unitarias (factura
  previa al siniestro → señal `factura_previa_al_siniestro`; fechas coherentes → sin señal).

A diferencia de la versión anterior del prototipo —que usaba un *mock* de fraude con un
*score* aleatorio y producía algún falso positivo no determinista—, el motor actual es
**determinista y auditable**, lo que elimina esa fuente de variabilidad y permite una
evaluación reproducible.

## 4.8 Validación complementaria

- **Suite de tests automatizados:** **47 tests** (pytest, SQLite en memoria) que cubren
  los agentes, la orquestación end-to-end, las herramientas, el motor antifraude, el RAG
  y la coherencia documental. Se ejecutan sin MariaDB ni Docker.
- **Extracción multimodal real (Agente C):** validada por separado con Claude Vision sobre
  un documento real (una factura), del que el modelo extrajo correctamente importe
  (3.200,00 €), fecha y emisor (la evaluación por lotes usa los tipos de documento, no
  imágenes reales, por lo que el VLM se demuestra de forma cualitativa en la interfaz).
- **Demostración CLI/Streamlit:** ejecución de los cinco caminos del flujo con el Chain of
  Thought visible.

## 4.9 Conclusiones de la evaluación

- El sistema alcanza una **precisión del 100 % sobre el dataset sintético de 32 casos**,
  con la matriz de confusión perfectamente diagonal. Este resultado valida la **corrección
  de la lógica del flujo** (validación → extracción → fraude → cobertura → resolución) y
  de los criterios de decisión.
- Las **capacidades de IA reales** quedan verificadas: el cribado OFAC bloquea a clientes
  sancionados, el RAG decide la cobertura recuperando la cláusula de póliza, y la extracción
  multimodal lee documentos reales.
- La **separación entre lógica determinista y razonamiento por LLM** se confirma acertada:
  la decisión es estable y reproducible (sin LLM), mientras que Claude enriquece la traza de
  auditoría y realiza la extracción multimodal cuando está disponible.

## 4.10 Limitaciones y trabajo futuro

- **Naturaleza del dataset.** Una precisión del 100 % sobre datos sintéticos diseñados para
  ejercitar la lógica determinista valida el *flujo*, no el rendimiento en producción. Una
  validación productiva requiere expedientes reales (anonimizados) con la decisión de
  gestores expertos como *ground truth*.
- **Tamaño.** 32 casos bastan para cubrir los caminos del flujo; se propone ampliar a varios
  cientos por muestreo de la distribución real.
- **Datos sintéticos.** La lista OFAC, las pólizas (RAG) y los baselines de importe son
  placeholders; su sustitución por las fuentes reales de Seguros Pepín es trabajo de la
  fase de producción.
- **Evaluación del VLM.** La extracción multimodal se valida cualitativamente; una métrica
  cuantitativa (F1 sobre campos extraídos) requiere un corpus etiquetado de documentos.

## Bibliografía

- Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020).
  *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv:2005.11401.
- Russell, S., & Norvig, P. (2021). *Artificial intelligence: A modern approach* (4.ª ed.).
  Pearson.
- Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022).
  *ReAct: Synergizing reasoning and acting in language models*. arXiv:2210.03629.
