# Manual de usuario — Smart-Claims Agent

**Seguros Pepín, S.A. — MVP agéntico de gestión de siniestros**
TFM Máster en Machine Learning e Inteligencia Artificial, OBS Business School

## Índice

1. [Introducción y público objetivo](#1-introducción-y-público-objetivo)
2. [Requisitos previos](#2-requisitos-previos)
3. [Configuración del entorno](#3-configuración-del-entorno)
4. [Puesta en marcha con Docker](#4-puesta-en-marcha-con-docker)
5. [Uso vía API REST](#5-uso-vía-api-rest)
6. [Uso vía CLI de demostración (sin Docker)](#6-uso-vía-cli-de-demostración-sin-docker)
7. [Interpretación de resultados](#7-interpretación-de-resultados)
8. [Inspección de la base de datos con Adminer](#8-inspección-de-la-base-de-datos-con-adminer)
9. [Resolución de problemas frecuentes](#9-resolución-de-problemas-frecuentes)
10. [Referencias](#10-referencias)

## 1. Introducción y público objetivo

Este manual describe el modo de operación del prototipo **Smart-Claims Agent** en su versión de entrega de TFM. No es un manual de usuario final orientado a un empleado de Seguros Pepín, S.A., sino un **manual operativo para el evaluador técnico** (director del TFM, tribunal académico o desarrollador que revise el prototipo). Su propósito es permitir reproducir, inspeccionar y validar el comportamiento del sistema de forma autónoma.

El sistema se opera principalmente a través de tres vías:

- **API REST** (interfaz primaria): permite enviar expedientes al orquestador y recibir las decisiones de forma programática, con documentación interactiva accesible en Swagger UI.
- **Dashboard Streamlit**: interfaz web que muestra el Chain of Thought de cada agente en tiempo real y un historial de los expedientes procesados. Útil para demostraciones visuales y para inspeccionar los razonamientos sin recurrir a la consola.
- **CLI de demostración** (interfaz sin dependencias externas): ejecuta cuatro casos representativos directamente sobre el orquestador Python, mostrando el Chain of Thought y la decisión final, sin necesidad de Docker ni de base de datos.

> **Nota sobre integraciones externas:** todas las herramientas que en producción consultarían sistemas reales de Seguros Pepín (motor antifraude, gestor documental, núcleo de pólizas, listas OFAC/ONU) están implementadas como **mocks deterministas**. El LLM (Claude de Anthropic) es **opcional**: si se proporciona la variable `ANTHROPIC_API_KEY`, enriquece el razonamiento de cada agente con cadenas de pensamiento generativas; si no se proporciona, el sistema utiliza un fallback de texto determinista y la demostración funciona de forma idéntica. Véase el apartado 3.3 para más detalles.

## 2. Requisitos previos

### 2.1 Opción A — Despliegue completo con Docker (recomendada)

| Requisito | Versión mínima | Notas |
|---|---|---|
| Docker Engine | 24.x | Incluye el demonio de contenedores |
| Docker Compose | v2 (plugin) | `docker compose` (sin guion) |
| Memoria RAM disponible | 4 GB | Para los cinco servicios en paralelo |
| Puertos libres | 8000, 8080, 8082, 8501, 3306 | Véase tabla de servicios en §4 |

Verificación rápida:

```bash
docker --version
docker compose version
```

### 2.2 Opción B — CLI de demostración sin Docker

| Requisito | Versión | Notas |
|---|---|---|
| Python | 3.11 | Versión exacta recomendada; 3.12 puede funcionar |
| Dependencias Python | — | Instaladas desde `backend/requirements.txt` |

En Windows, el lanzador oficial de Python es `py`:

```powershell
py --version
```

No se requiere MariaDB ni ChromaDB para la CLI; la persistencia se omite con un aviso de log y el flujo continúa sin errores.

## 3. Configuración del entorno

### 3.1 Crear el fichero `.env`

El fichero `.env` es la única fuente de configuración del sistema. Se parte de la plantilla incluida en el repositorio:

```bash
# Desde la raíz del repositorio
cp .env.example .env
```

En Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

### 3.2 Variables de entorno relevantes

Editar `.env` con los valores adecuados para el entorno de evaluación. La tabla siguiente describe las variables más importantes:

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | (vacío) | Clave API de Anthropic (opcional; véase §3.3) |
| `DB_USER` | `claims_user` | Usuario de aplicación de MariaDB |
| `DB_PASSWORD` | `claims_dev` | Contraseña del usuario de aplicación |
| `DB_HOST` | `mariadb` | Hostname del servicio MariaDB |
| `DB_PORT` | `3306` | Puerto de MariaDB |
| `DB_NAME` | `smart_claims` | Nombre de la base de datos |
| `CHROMADB_HOST` | `chromadb` | Hostname del servicio ChromaDB |
| `CHROMADB_PORT` | `8000` | Puerto interno de ChromaDB |
| `BACKEND_URL` | `http://backend:8000` | URL del backend (referencia interna entre contenedores) |
| `HITL_AMOUNT_THRESHOLD` | `5000` | Umbral de importe (€) para activar revisión humana |
| `MARIADB_ROOT_PASSWORD` | `root_dev` | Contraseña root de MariaDB |

### 3.3 La clave `ANTHROPIC_API_KEY` y el modo fallback

La variable `ANTHROPIC_API_KEY` controla si el razonamiento de los agentes se genera mediante el modelo Claude o mediante el texto determinista de fallback:

- **Con clave válida:** cada agente invoca a Claude (`claude-sonnet-4-6`) a través del helper `reason()` para generar el razonamiento Chain of Thought. Requiere conexión a internet y una clave de pago activa.
- **Sin clave (o clave vacía):** el módulo `app/agents/reasoning.py` detecta la ausencia de la variable y retorna el texto de fallback predefinido en cada nodo. **La decisión final del orquestador es idéntica en ambos casos**, ya que la lógica de enrutamiento es determinista (basada en cobertura, importe y documentación), no dependiente del LLM. Para la evaluación académica del prototipo, el modo fallback es suficiente.

Para una demostración con razonamiento enriquecido, introducir una clave válida de Anthropic en `.env` antes de levantar los contenedores. Véase la documentación de la API de Anthropic para la gestión de claves (Anthropic, 2024).

### 3.4 Umbral HITL

El parámetro `HITL_AMOUNT_THRESHOLD` (valor por defecto: `5000`) determina el importe máximo en euros por debajo del cual el agente resolutor (Agente E) puede aprobar un pago de forma autónoma. Expedientes con importe superior son derivados automáticamente a revisión humana (`REVISION_HUMANA`). Este valor es ajustable sin necesidad de recompilar el código.

## 4. Puesta en marcha con Docker

### 4.1 Arranque del sistema

Desde la **raíz del repositorio**, con el fichero `.env` ya configurado:

```bash
docker compose up -d --build
```

Docker Compose construirá las imágenes locales del backend y el frontend, descargará el resto de imágenes y levantará todos los servicios en segundo plano. El primer arranque puede tardar entre 2 y 5 minutos según la velocidad de descarga.

Para ver los logs en tiempo real durante el arranque:

```bash
docker compose logs -f backend
```

### 4.2 Servicios y URLs

| Servicio | Contenedor | Puerto (host) | URL de acceso | Descripción |
|---|---|---|---|---|
| Backend FastAPI | `sca-backend` | 8000 | `http://localhost:8000` | API REST principal |
| Frontend Streamlit | `sca-frontend` | 8501 | `http://localhost:8501` | Dashboard de demostración |
| ChromaDB | `sca-chromadb` | 8080 | `http://localhost:8080` | Vector store RAG |
| MariaDB | `sca-mariadb` | 3306 | `localhost:3306` | Base de datos relacional |
| Adminer | `sca-adminer` | 8082 | `http://localhost:8082` | Inspector web de BD |

> **Nota sobre dependencias de arranque:** el contenedor `sca-backend` espera a que MariaDB supere su healthcheck antes de iniciarse. Si el backend aparece como restarting en los primeros segundos, es comportamiento normal.

### 4.3 Verificación del sistema

Una vez levantados los contenedores, verificar que el backend responde correctamente:

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status": "ok", "version": "0.5.0"}
```

Verificar también el estado de los agentes:

```bash
curl http://localhost:8000/api/v1/agents/status
```

Respuesta esperada (resumen):

```json
{
  "pattern": "Supervisor (Hub-and-Spoke) sobre LangGraph",
  "agent_count": 6,
  "agents": [
    {"id": "A", "name": "Orchestrator", "status": "operational"},
    {"id": "B", "name": "Document Validator", "status": "operational"},
    {"id": "C", "name": "Multimodal Extractor", "status": "operational"},
    {"id": "D", "name": "Coverage Checker", "status": "operational"},
    {"id": "E", "name": "Claim Resolver", "status": "operational"},
    {"id": "G", "name": "Fraud Compliance", "status": "operational"}
  ]
}
```

### 4.4 Parada del sistema

```bash
docker compose down
```

Para parar y eliminar también los volúmenes de datos:

```bash
docker compose down -v
```

## 5. Uso vía API REST

### 5.1 Documentación interactiva (Swagger UI)

FastAPI genera automáticamente una interfaz Swagger disponible en:

```
http://localhost:8000/docs
```

Desde esta URL es posible explorar todos los endpoints, ver los esquemas de request/response y ejecutar peticiones directamente desde el navegador (FastAPI, 2024).

### 5.2 Endpoint principal: procesado de un expediente

**`POST /api/v1/claims/`**

Procesa un expediente de siniestro a través del grafo de agentes y devuelve la decisión, la traza de razonamiento y si se requiere intervención humana.

#### Campos del cuerpo de la petición

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `claim_id` | `string` | No | Si se omite, el backend genera uno automático con formato `CLM-XXXXXXXX` |
| `client_id` | `string` | Sí | Identificador del asegurado |
| `client_email` | `string` | No (default: `cliente@example.com`) | Email para notificaciones |
| `claim_type` | `string` | Sí | Tipo de siniestro (véase §5.3) |
| `channel` | `string` | No (default: `email`) | Canal de entrada: `email`, `web`, `whatsapp` |
| `amount_requested` | `float` | No (default: `0.0`) | Importe reclamado en euros |
| `documents` | `list[string]` | No (default: `[]`) | Lista de documentos aportados |
| `text` | `string` | No (default: `""`) | Descripción libre del siniestro |

#### Campos de la respuesta

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `string` | Identificador del expediente procesado |
| `status` | `string` | Estado final: `resolved`, `rejected`, `pending_review` o `validating` |
| `decision` | `string` | Decisión final: `PAGO`, `RECHAZO`, `RECHAZO_FRAUDE`, `REVISION_HUMANA` o `INFO_REQUERIDA` |
| `amount_requested` | `float` | Importe solicitado |
| `amount_paid` | `float` o `null` | Importe efectivamente abonado (solo en pagos aprobados) |
| `hitl_required` | `boolean` | `true` si el expediente requiere revisión humana |
| `termination_reason` | `string` o `null` | Causa de la terminación del flujo |
| `reasoning_trace` | `list[string]` | Chain of Thought completo, una entrada por agente invocado |

### 5.3 Tipos de siniestro y documentos requeridos

El mock de `validate_documents` exige un conjunto de documentos distinto según el tipo de siniestro:

| `claim_type` | Documentos requeridos | Cobertura mock |
|---|---|---|
| `danys_propis` | `foto_danys`, `factura`, `denuncia_companyia` | Cubierto (límite 10.000 €, franquicia 300 €) |
| `responsabilitat` | `foto_danys`, `acta_policial`, `dades_tercer` | Cubierto (límite 50.000 €, sin franquicia) |
| `robatori` | `acta_policial`, `llista_objectes_robats` | Cubierto (límite 8.000 €, franquicia 500 €) |
| `danys_mecanics` | `informe_taller`, `factura` | **No cubierto** (exclusión SP-PCS-009 § 7.3) |
| `default` | `foto_danys`, `factura` | No catalogado, sin cobertura |

### 5.4 Ejemplos `curl` — los cinco caminos del flujo

#### Camino 1: PAGO — daños propios, importe bajo, documentación completa

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-PAGO-01",
    "client_id": "C-A",
    "claim_type": "danys_propis",
    "channel": "email",
    "amount_requested": 3200.0,
    "documents": ["foto_danys", "factura", "denuncia_companyia"],
    "text": "Colisión frontal al aparcar. Daños en la carrocería delantera."
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-PAGO-01",
  "status": "resolved",
  "decision": "PAGO",
  "amount_paid": 2900.0,
  "hitl_required": false,
  "termination_reason": "pago aprobado",
  "reasoning_trace": [
    "Agente A: expediente CLM-PAGO-01 ...",
    "Agente G: riesgo de fraude 0.12, sin indicios relevantes.",
    "Agente B: documentación completa y conforme.",
    "Agente C: extraídos 3 documentos con confianza media 0.91.",
    "Agente D: siniestro cubierto según SP-PCS-009 § 3.2.",
    "Agente E: cobertura confirmada y 2900.00 EUR dentro del umbral; PAGO aprobado."
  ]
}
```

El importe pagado (2900 €) corresponde a 3200 € reclamados menos 300 € de franquicia.

#### Camino 2: REVISION_HUMANA — importe supera el umbral HITL

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-HITL-01",
    "client_id": "C-B",
    "claim_type": "responsabilitat",
    "channel": "web",
    "amount_requested": 8500.0,
    "documents": ["foto_danys", "acta_policial", "dades_tercer"],
    "text": "Accidente de tráfico con vehículo de tercero. Daños materiales importantes."
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-HITL-01",
  "status": "pending_review",
  "decision": "REVISION_HUMANA",
  "amount_paid": null,
  "hitl_required": true,
  "termination_reason": "importe 8500.0 EUR supera umbral HITL (5000.0 EUR)"
}
```

#### Camino 3: RECHAZO — tipo sin cobertura

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-RECH-01",
    "client_id": "C-C",
    "claim_type": "danys_mecanics",
    "channel": "email",
    "amount_requested": 1000.0,
    "documents": ["informe_taller", "factura"],
    "text": "Avería del motor por desgaste. Solicito cobertura de reparación."
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-RECH-01",
  "status": "rejected",
  "decision": "RECHAZO",
  "hitl_required": false,
  "termination_reason": "rechazado por no cobertura"
}
```

#### Camino 4: INFO_REQUERIDA — documentación incompleta

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-INFO-01",
    "client_id": "C-D",
    "claim_type": "danys_propis",
    "channel": "email",
    "amount_requested": 1000.0,
    "documents": ["factura"],
    "text": "Daños en el vehículo por piedra en autopista. Adjunto factura."
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-INFO-01",
  "status": "validating",
  "decision": "INFO_REQUERIDA",
  "hitl_required": false,
  "termination_reason": "documentacion incompleta: faltan foto_danys, denuncia_companyia"
}
```

#### Camino 5: RECHAZO_FRAUDE — alerta del cribado antifraude

Este caso depende del valor aleatorio generado por el mock de `check_fraud`. Si el `risk_score` supera 0,30, el supervisor termina el flujo con la causa `RECHAZO_FRAUDE`. Para reproducirlo deterministamente, se puede usar una semilla específica desde la CLI (véase §6).

### 5.5 Otros endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/v1/claims/` | GET | Lista los expedientes con paginación y filtro opcional por estado |
| `/api/v1/claims/{claim_id}` | GET | Devuelve el expediente con todas sus decisiones |
| `/api/v1/claims/{claim_id}/trace` | GET | Devuelve únicamente el Chain of Thought completo |
| `/api/v1/agents/status` | GET | Información sobre los agentes del sistema |
| `/health` | GET | Comprobación de salud del servicio |

Ejemplo de consulta de un expediente:

```bash
curl -s http://localhost:8000/api/v1/claims/CLM-PAGO-01
```

Si el expediente no existe, la respuesta es `HTTP 404`.

## 6. Uso vía CLI de demostración (sin Docker)

### 6.1 Instalación de dependencias

Desde la carpeta `backend/` del repositorio:

```powershell
# Windows
py -m pip install -r requirements.txt
```

```bash
# Linux / macOS
python3.11 -m pip install -r requirements.txt
```

### 6.2 Ejecución

```powershell
# Windows (desde la raíz del repositorio)
py backend/scripts/run_demo.py
```

```bash
# Linux / macOS (desde la raíz del repositorio)
python3.11 backend/scripts/run_demo.py
```

O alternativamente con Docker, si el contenedor del backend está levantado:

```bash
docker exec -it sca-backend python scripts/run_demo.py
```

### 6.3 Casos de demostración

El script ejecuta cuatro expedientes predefinidos con una semilla aleatoria fija (`random.seed(7)`) para garantizar reproducibilidad en cada ejecución ante el tribunal:

| Expediente | `claim_type` | Importe | Documentos | Decisión esperada |
|---|---|---|---|---|
| `DEMO-PAGO` | `danys_propis` | 3.200 € | Completos | `PAGO` |
| `DEMO-HITL` | `responsabilitat` | 8.500 € | Completos | `REVISION_HUMANA` |
| `DEMO-RECHAZO` | `danys_mecanics` | 1.000 € | Completos | `RECHAZO` o `RECHAZO_FRAUDE` (según semilla) |
| `DEMO-INFO` | `danys_propis` | 1.000 € | Solo `factura` | `INFO_REQUERIDA` |

### 6.4 Salida esperada

Para cada expediente, la CLI muestra un bloque con el siguiente formato:

```
------------------------------------------------------------------------------
  Expediente: DEMO-PAGO
  Escenario:  Pago automatico (cobertura + importe bajo)
  Tipo:       danys_propis  |  Importe: 3200.0 EUR
------------------------------------------------------------------------------

  Razonamiento (Chain of Thought):
    1. Agente A: expediente DEMO-PAGO de tipo 'danys_propis' por importe 3200.0 EUR...
    2. Agente G: riesgo de fraude 0.12, sin indicios relevantes.
    3. Agente B: documentación completa y conforme.
    4. Agente C: extraídos 3 documentos con confianza media 0.91.
    5. Agente D: siniestro 'danys_propis' cubierto según SP-PCS-009 § 3.2.
    6. Agente E: cobertura confirmada y 2900.00 EUR dentro del umbral; PAGO aprobado.

  >>> Decision:  PAGO
      Estado:    resolved
      HITL:      False
      Importe pagado: 2900.0 EUR
```

La traza muestra el razonamiento de cada agente en el orden en que intervino en el grafo: A (triaje) → G (antifraude) → B (validación documental) → C (extracción multimodal) → D (verificación de póliza) → E (resolución).

> **Sin MariaDB:** la CLI imprime un aviso de log del tipo `WARNING: No se han podido persistir las decisiones de DEMO-PAGO: ...` pero continúa procesando todos los expedientes. La lógica agéntica es independiente de la persistencia.

## 7. Interpretación de resultados

### 7.1 Decisiones posibles

| Decisión | Significado | `hitl_required` | Estado en BD |
|---|---|---|---|
| `PAGO` | Expediente aprobado. El importe se procesa de forma autónoma (mock de transferencia). | `false` | `resolved` |
| `RECHAZO` | Expediente rechazado por ausencia de cobertura en póliza. Se envía notificación al cliente. | `false` | `rejected` |
| `RECHAZO_FRAUDE` | Expediente bloqueado por el cribado antifraude (Agente G marca el caso como flagged). | `false` | `rejected` |
| `REVISION_HUMANA` | El importe supera el umbral `HITL_AMOUNT_THRESHOLD`. Un operador humano debe intervenir. | `true` | `pending_review` |
| `INFO_REQUERIDA` | Documentación incompleta. El expediente queda en espera de los documentos pendientes. | `false` | `validating` |

### 7.2 El campo `hitl_required`

El campo booleano `hitl_required` en la respuesta indica de forma explícita si el expediente ha sido derivado a revisión humana. Se activa únicamente cuando la decisión es `REVISION_HUMANA` por superar el umbral de importe. Otros caminos terminales (rechazo por fraude, rechazo por no cobertura, solicitud de información) no requieren revisión humana porque la decisión automática es ya definitiva o pasiva (a la espera del cliente).

El diseño de Human-in-the-Loop responde a los principios de IA responsable recogidos en la literatura sobre sistemas agénticos (Russell, 2019; Amershi et al., 2019): ningún pago de alto valor se resuelve de forma totalmente autónoma.

### 7.3 El campo `reasoning_trace` — Chain of Thought

`reasoning_trace` es una lista de cadenas donde cada elemento corresponde al razonamiento de un agente del grafo. La lista crece a medida que avanza el flujo, gracias a los acumuladores `Annotated[list, operator.add]` definidos en `ClaimState`. El primer elemento corresponde al Agente A (triaje), los siguientes a los agentes especializados invocados (G, B, C, D, E).

El Chain of Thought visible permite al evaluador:

- Verificar qué agentes intervinieron y en qué orden.
- Comprobar si el razonamiento proviene del LLM (texto más elaborado, con formato Markdown) o del fallback determinista (texto más esquemático).
- Detectar el motivo exacto de un rechazo, una solicitud de información o una derivación a HITL.

Para consultar la traza completa de un expediente persistido, el endpoint `/api/v1/claims/{id}/trace` la devuelve formateada como lista de decisiones con su marca temporal y nivel de confianza.

## 8. Inspección de la base de datos con Adminer

### 8.1 Acceso a Adminer

Con el sistema Docker levantado, abrir en el navegador:

```
http://localhost:8082
```

Adminer es una herramienta web ligera de administración de bases de datos (Vrána, 2024). En la pantalla de inicio, introducir los siguientes datos de conexión:

| Campo | Valor |
|---|---|
| Sistema | MariaDB |
| Servidor | `mariadb` |
| Usuario | `claims_user` |
| Contraseña | `claims_dev` (o el valor configurado en `.env`) |
| Base de datos | `smart_claims` |

### 8.2 Tablas del esquema

La base de datos `smart_claims` contiene tres tablas:

| Tabla | Descripción |
|---|---|
| `claims` | Un registro por expediente procesado. Columnas principales: `id`, `client_id`, `claim_type`, `channel`, `status`, `amount_requested`, `amount_approved`, `created_at`. |
| `agent_decisions` | Una fila por decisión de cada agente. Columnas: `claim_id` (FK), `agent`, `action`, `reasoning` (texto completo del CoT), `confidence`, `hitl_required`, `created_at`. |
| `hitl_feedback` | Tabla preparada para el feedback del operador humano en casos HITL. Columnas: `claim_id`, `decision_id` (FK), `reviewer`, `original_action`, `final_action`, `override_reason`. Vacía en el MVP actual; se alimentará en la siguiente fase. |

### 8.3 Consultar la traza de decisiones de un expediente

Para ver el ciclo completo de un expediente, ejecutar la siguiente consulta SQL desde la opción **Ejecutar SQL** de Adminer:

```sql
SELECT
    ad.created_at,
    ad.agent,
    ad.action,
    ad.reasoning,
    ad.confidence,
    ad.hitl_required
FROM agent_decisions ad
WHERE ad.claim_id = 'CLM-PAGO-01'
ORDER BY ad.id ASC;
```

El resultado muestra la secuencia cronológica de todos los agentes que intervinieron, con su razonamiento completo y si cada uno de ellos marcó el paso como requirente de revisión humana.

Para ver el estado final del expediente:

```sql
SELECT id, claim_type, status, amount_requested, amount_approved, created_at
FROM claims
WHERE id = 'CLM-PAGO-01';
```

## 9. Resolución de problemas frecuentes

### 9.1 Sin `ANTHROPIC_API_KEY` — el sistema usa el fallback

**Síntoma:** el razonamiento en `reasoning_trace` es breve y esquemático (p. ej., `"Agente E: cobertura confirmada y 2900.00 EUR dentro del umbral; PAGO aprobado."`).

**Causa:** la variable `ANTHROPIC_API_KEY` no está configurada o es inválida. El módulo `reasoning.py` cae al texto de fallback predefinido.

**Solución:** si se desea el razonamiento enriquecido con el LLM, añadir una clave válida de Anthropic en `.env` y reiniciar los contenedores:

```bash
docker compose restart backend
```

El comportamiento de la demo es correcto en cualquier caso; el fallback es un comportamiento esperado del diseño.

### 9.2 Sin MariaDB — la CLI muestra un aviso pero continúa

**Síntoma al usar la CLI:** aparece en los logs una línea similar a:

```
WARNING root: No se han podido persistir las decisiones de DEMO-PAGO: ...
```

**Causa:** la CLI de demostración se ejecuta sin el servicio MariaDB levantado. `process_claim` captura la excepción de conexión en un bloque `try/except` y continúa el flujo.

**Solución:** este comportamiento es intencional y documentado en el diseño del MVP. Para persistencia completa, usar el despliegue Docker (§4).

### 9.3 Puerto ocupado al arrancar Docker

**Síntoma:** error al ejecutar `docker compose up -d`, similar a:

```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8000 -> ...
```

**Causa:** alguno de los puertos requeridos (8000, 8080, 8082, 8501, 3306) está en uso por otro proceso en el host.

**Solución:** identificar y detener el proceso que ocupa el puerto. En Windows:

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Alternativamente, modificar el mapeo de puertos en `docker-compose.yml` (columna izquierda del par `host:contenedor`).

### 9.4 El backend no arranca (`sca-backend` en estado `restarting`)

**Causa más frecuente:** MariaDB no ha completado su inicialización antes de que el backend intente conectarse.

**Solución:** esperar entre 30 y 60 segundos y verificar de nuevo:

```bash
docker compose ps
docker compose logs backend --tail=30
```

Si el problema persiste, verificar que las variables `DB_*` en `.env` son consistentes con las definidas en el bloque `mariadb` de `docker-compose.yml`.

### 9.5 Error `404 Not Found` en `GET /api/v1/claims/{id}`

**Causa:** el expediente con ese identificador no existe en la base de datos. Los expedientes solo se persisten si el sistema Docker está levantado y la conexión a MariaDB es correcta. La CLI de demostración no persiste resultados si MariaDB no está disponible.

**Solución:** enviar primero el expediente mediante `POST /api/v1/claims/` con el sistema Docker activo, y consultar inmediatamente después con el mismo `claim_id`.

### 9.6 Mensaje `RuntimeError: Event loop is closed` al ejecutar la CLI

**Síntoma:** la CLI termina con un *traceback* del tipo:

```
Exception ignored in: <function Connection.__del__ ...>
RuntimeError: Event loop is closed
```

**Causa:** el driver `aiomysql` intenta cerrar sus conexiones después de que el bucle asíncrono ya se ha cerrado. Es un aviso cosmético que no afecta al resultado del flujo.

**Solución:** se puede ignorar, o bien añadir un `await engine.dispose()` al final de `main()` en `run_demo.py` para liberar las conexiones de forma ordenada antes del cierre del bucle.

## 10. Referencias

Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., y Horvitz, E. (2019). Software engineering for machine learning: A case study. *Proceedings of the 41st International Conference on Software Engineering: Software Engineering in Practice*, 291–300. https://doi.org/10.1109/ICSE-SEIP.2019.00042

Anthropic. (2024). *Claude API documentation*. https://docs.anthropic.com

FastAPI. (2024). *FastAPI documentation: Interactive API docs*. https://fastapi.tiangolo.com/features/

Russell, S. (2019). *Human compatible: Artificial intelligence and the problem of control*. Viking.

Vrána, J. (2024). *Adminer — Database management in a single PHP file*. https://www.adminer.org
