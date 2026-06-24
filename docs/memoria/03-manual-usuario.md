# Manual de usuario — Smart-Claims Agent

**Seguros Pepín, S.A. — MVP agéntico de gestión de siniestros**
TFM Máster en Machine Learning e Inteligencia Artificial, OBS Business School

---

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

---

## 1. Introducción y público objetivo

Este manual describe el modo de operación del prototipo **Smart-Claims Agent** en su versión de entrega de TFM. No es un manual de usuario final orientado a un empleado de Seguros Pepín, S.A., sino un **manual operativo para el evaluador técnico** (director del TFM, tribunal académico o desarrollador que revise el prototipo). Su propósito es permitir reproducir, inspeccionar y validar el comportamiento del sistema de forma autónoma.

El sistema se opera principalmente a través de dos vías:

- **API REST** (interfaz primaria): permite enviar expedientes al agente orquestrador y recibir las decisiones de forma programática.
- **CLI de demostración** (interfaz secundaria, sin dependencias externas): ejecuta cuatro casos representativos directamente sobre el orquestrador Python, mostrando el Chain of Thought y la decisión final, sin necesidad de Docker ni de base de datos.

La interfaz Streamlit (puerto 8501) está incluida en el despliegue Docker pero **no es prioritaria en esta entrega**; el flujo agéntico completo se puede validar íntegramente a través de los dos modos anteriores.

> **Nota sobre integraciones externas:** todas las herramientas que en producción consultarían sistemas reales de Seguros Pepín (pasarela antifrau, gestor documental, núcleo de pólizas, OFAC/ONU) están implementadas como **mocks deterministas**. El LLM (Claude de Anthropic) es **opcional**: si se proporciona la variable `ANTHROPIC_API_KEY`, enriquece el razonamiento de cada agente con cadenas de pensamiento generativas; si no se proporciona, el sistema utiliza un fallback de texto determinista y la demostración funciona de forma idéntica. Véase el apartado 3 para más detalles.

---

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

---

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

| Variable | Valor por defecto en `.env.example` | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-XXXX...` | Clave API de Anthropic (opcional; véase §3.3) |
| `DB_ROOT_PASSWORD` | `root_s3cret_dev` | Contraseña root de MariaDB |
| `DB_NAME` | `smart_claims` | Nombre de la base de datos |
| `DB_USER` | `claims_user` | Usuario de aplicación de MariaDB |
| `DB_PASSWORD` | `claims_s3cret_dev` | Contraseña del usuario de aplicación |
| `DB_HOST` | `mariadb` | Hostname del servicio MariaDB (nombre de servicio Docker) |
| `DB_PORT` | `3306` | Puerto de MariaDB |
| `CHROMA_HOST` | `chromadb` | Hostname del servicio ChromaDB |
| `CHROMA_PORT` | `8000` | Puerto interno de ChromaDB |
| `CHROMA_COLLECTION` | `pepin_policies` | Nombre de la colección vectorial |
| `BACKEND_URL` | `http://backend:8000` | URL del backend (referencia interna entre contenedores) |
| `HITL_AMOUNT_THRESHOLD` | `5000.0` | Umbral de importe (€) para activar revisión humana (HITL) |
| `ENVIRONMENT` | `development` | Entorno de ejecución |
| `LOG_LEVEL` | `INFO` | Nivel de log del backend |

### 3.3 La clave `ANTHROPIC_API_KEY` y el modo fallback

La variable `ANTHROPIC_API_KEY` controla si el razonamiento de los agentes se genera mediante el modelo Claude (Anthropic) o mediante el texto determinista de fallback:

- **Con clave válida:** cada agente invoca la API de Anthropic para generar el razonamiento Chain of Thought. Requiere conexión a internet y una clave de pago activa.
- **Sin clave (o clave vacía):** el módulo `app/agents/reasoning.py` detecta la ausencia de la variable y retorna el texto de fallback predefinido en cada nodo. **La decisión final del orquestrador es idéntica en ambos casos**, ya que la lógica de routing es determinista (basada en cobertura, importe y documentación), no dependiente del LLM. Para la evaluación académica del prototipo, el modo fallback es suficiente.

> Para una demostración con razonamiento enriquecido, introducir una clave válida de Anthropic en `.env` antes de levantar los contenedores. Véase la documentación de la API de Anthropic para la gestión de claves (Anthropic, 2024).

### 3.4 Umbral HITL

El parámetro `HITL_AMOUNT_THRESHOLD` (valor por defecto: `5000.0`) determina el importe máximo en euros por debajo del cual el agente resolutivo (Agent E) puede aprobar un pago de forma autónoma. Expedientes con importe superior son derivados automáticamente a revisión humana (`REVISIÓN_HUMANA`). Este valor es ajustable sin necesidad de recompilar el código.

---

## 4. Puesta en marcha con Docker

### 4.1 Arranque del sistema

Desde la **raíz del repositorio**, con el fichero `.env` ya configurado:

```bash
docker compose up -d
```

Docker Compose descargará las imágenes necesarias (si no están en caché), construirá las imágenes locales del backend y el frontend, y levantará todos los servicios en segundo plano. El primer arranque puede tardar entre 2 y 5 minutos según la velocidad de descarga.

Para ver los logs en tiempo real durante el arranque:

```bash
docker compose logs -f backend
```

### 4.2 Servicios y URLs

| Servicio | Contenedor | Puerto (host) | URL de acceso | Descripción |
|---|---|---|---|---|
| Backend FastAPI | `sca-backend` | 8000 | `http://localhost:8000` | API REST principal |
| Frontend Streamlit | `sca-frontend` | 8501 | `http://localhost:8501` | Interfaz web (no prioritaria) |
| ChromaDB | `sca-chromadb` | 8080 | `http://localhost:8080` | Vector store RAG |
| MariaDB | `sca-mariadb` | 3306 | `localhost:3306` | Base de datos relacional |
| Adminer | `sca-adminer` | 8082 | `http://localhost:8082` | Inspector web de BD |

> **Nota sobre dependencias de arranque:** el contenedor `sca-backend` espera a que MariaDB supere su healthcheck antes de iniciarse (la comprobación se realiza cada 10 s con un máximo de 5 reintentos). Si el backend aparece como restarting en los primeros segundos, es comportamiento normal.

### 4.3 Verificación del sistema

Una vez levantados los contenedores, verificar que el backend responde correctamente:

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status": "ok", "version": "0.2.0"}
```

Verificar también el estado de los agentes:

```bash
curl http://localhost:8000/api/v1/agents/status
```

Respuesta esperada:

```json
{
  "agents": [
    {"id": "agent_a", "status": "implemented"},
    {"id": "agent_b", "status": "implemented"},
    {"id": "agent_c", "status": "implemented"},
    {"id": "agent_d", "status": "implemented"},
    {"id": "agent_e", "status": "implemented"},
    {"id": "agent_g", "status": "implemented"}
  ]
}
```

### 4.4 Parada del sistema

```bash
docker compose down
```

Para parar y eliminar también los volúmenes de datos (MariaDB y ChromaDB):

```bash
docker compose down -v
```

---

## 5. Uso vía API REST

### 5.1 Documentación interactiva (Swagger UI)

FastAPI genera automáticamente una interfaz Swagger disponible en:

```
http://localhost:8000/docs
```

Desde esta URL es posible explorar todos los endpoints, ver los esquemas de request/response y ejecutar peticiones directamente desde el navegador, sin necesidad de herramientas adicionales. Esta es la forma más rápida de explorar la API de forma interactiva (FastAPI, 2024).

### 5.2 Endpoint principal: procesado de un expediente

**`POST /api/v1/claims`**

Procesa un expediente de siniestro a través del grafo de agentes y devuelve la decisión, la traza de razonamiento y si se requiere intervención humana.

#### Campos del cuerpo de la petición (`ClaimRequest`)

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `claim_id` | `string` | Sí | Identificador único del expediente |
| `client_id` | `string` | Sí | Identificador del asegurado |
| `claim_type` | `string` | Sí | Tipo de siniestro (véase §5.3) |
| `channel` | `string` | No (default: `"email"`) | Canal de entrada: `email`, `web`, `whatsapp` |
| `text` | `string` | Sí | Descripción libre del siniestro |
| `amount_requested` | `float` | No | Importe reclamado en euros |
| `doc_types` | `list[string]` | No (default: `[]`) | Lista de documentos aportados |

> **Nota:** el campo `text` está declarado en el modelo `ClaimRequest` del router pero no se propaga al orquestrador en la implementación actual del MVP (se recibe y valida, pero la lógica de decisión usa `claim_type`, `amount_requested` y `doc_types`). Esto es un área de mejora identificada para la fase de producción.

#### Campos de la respuesta (`ClaimResponse`)

| Campo | Tipo | Descripción |
|---|---|---|
| `claim_id` | `string` | Identificador del expediente procesado |
| `status` | `string` | Estado interno del expediente (p. ej., `resolved`, `rejected`, `pending_review`) |
| `message` | `string` | Mensaje de confirmación de procesado |
| `decision` | `string` | Decisión final del agente (véase §7) |
| `hitl_required` | `boolean` | `true` si el expediente requiere revisión humana |
| `reasoning_trace` | `list[string]` | Traza Chain of Thought del paso decisivo |

#### Tipos de siniestro válidos en el mock

| `claim_type` | Cobertura mock | Comportamiento esperado |
|---|---|---|
| `danys_propis` | Cubierto | PAGO (si importe ≤ umbral y docs completos) |
| `responsabilitat` | Cubierto | REVISIÓN_HUMANA (si importe > umbral) |
| `robatori` | Cubierto | PAGO o REVISIÓN_HUMANA según importe |
| `danys_mecànics` | **No cubierto** | RECHAZO (sin cobertura en póliza) |

### 5.3 Ejemplos `curl` — los cuatro caminos del orquestrador

#### Camino 1: PAGO — daños propios, importe bajo, documentación completa

```bash
curl -s -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-PAGO-01",
    "client_id": "C-A",
    "claim_type": "danys_propis",
    "channel": "email",
    "text": "Colisió frontal al garatge. Danys a la carrosseria delantera.",
    "amount_requested": 3200.0,
    "doc_types": ["foto_danys", "factura", "acta_policial"]
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-PAGO-01",
  "status": "resolved",
  "message": "Reclamació processada.",
  "decision": "PAGO",
  "hitl_required": false,
  "reasoning_trace": ["Agent E: cobertura confirmada i import 3200.0€ dins del llindar; s'aprova el PAGAMENT de ...€."]
}
```

#### Camino 2: REVISIÓN_HUMANA — importe supera el umbral HITL

```bash
curl -s -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-HITL-01",
    "client_id": "C-B",
    "claim_type": "responsabilitat",
    "channel": "web",
    "text": "Accident de trànsit amb vehicle de tercers. Danys materials importants.",
    "amount_requested": 8500.0,
    "doc_types": ["foto_danys", "factura", "acta_policial"]
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-HITL-01",
  "status": "pending_review",
  "decision": "REVISIÓN_HUMANA",
  "hitl_required": true,
  "reasoning_trace": ["Agent E: l'import 8500.0€ supera el llindar de 5000.0€; es deriva a REVISIÓ HUMANA."]
}
```

#### Camino 3: RECHAZO — tipo sin cobertura

```bash
curl -s -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-RECH-01",
    "client_id": "C-C",
    "claim_type": "danys_mecànics",
    "channel": "email",
    "text": "Avaria del motor per desgast. Sol·licito cobertura de reparació.",
    "amount_requested": 1000.0,
    "doc_types": ["foto_danys", "factura", "acta_policial"]
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-RECH-01",
  "status": "rejected",
  "decision": "RECHAZO",
  "hitl_required": false,
  "reasoning_trace": ["Agent E: el sinistre 'danys_mecànics' no té cobertura (...). Es RECHAZA."]
}
```

#### Camino 4: SOLICITUD_INFO — documentación incompleta

```bash
curl -s -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-INFO-01",
    "client_id": "C-D",
    "claim_type": "danys_propis",
    "channel": "email",
    "text": "Danys al vehicle per pedra a l autopista. Adjunto factura.",
    "amount_requested": 1000.0,
    "doc_types": ["factura"]
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-INFO-01",
  "status": "open",
  "decision": "SOLICITUD_INFO",
  "hitl_required": false,
  "reasoning_trace": ["Agent B: falten documents ['foto_danys', 'acta_policial']; se sol·licita informació addicional al client..."]
}
```

En este caso, el agente B detecta que faltan `foto_danys` y `acta_policial` (los documentos obligatorios son `foto_danys`, `factura` y `acta_policial`) y detiene el flujo solicitando los documentos al cliente.

### 5.4 Consulta de un expediente por ID

**`GET /api/v1/claims/{claim_id}`**

Devuelve los datos del expediente junto con el log de decisiones de todos los agentes que intervinieron:

```bash
curl -s http://localhost:8000/api/v1/claims/CLM-PAGO-01
```

Si el expediente no existe en la base de datos, la respuesta es `HTTP 404` con el mensaje `"Expedient no trobat"`.

---

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

O equivalentemente, desde dentro de `backend/`:

```powershell
cd backend
py scripts/run_demo.py
```

### 6.3 Casos de demostración

El script ejecuta cuatro expedientes predefinidos con una semilla aleatoria fija (`random.seed(7)`) para garantizar reproducibilidad en cada ejecución ante el tribunal:

| Expediente | `claim_type` | Importe | Documentos | Decisión esperada |
|---|---|---|---|---|
| `DEMO-PAGO` | `danys_propis` | 3.200 € | Completos | `PAGO` |
| `DEMO-HITL` | `responsabilitat` | 8.500 € | Completos | `REVISIÓN_HUMANA` |
| `DEMO-RECHAZO` | `danys_mecànics` | 1.000 € | Completos | `RECHAZO` |
| `DEMO-INFO` | `danys_propis` | 1.000 € | Solo `factura` | `SOLICITUD_INFO` |

### 6.4 Salida esperada

Para cada expediente, la CLI muestra un bloque con el siguiente formato:

```
======================================================================
EXPEDIENT: DEMO-PAGO  (danys_propis, 3200.0€)
----------------------------------------------------------------------
Raonament (Chain of Thought):
  1. Agent G: risc de frau 0.xx; sense indicis rellevants.
  2. Agent B: documentació completa i vàlida; manquen cap document.
  3. Agent C: dades extretes {...} amb confiança 0.xx.
  4. Agent D: sinistre 'danys_propis' cobert; import net pagable ...€ (secció ...).
  5. Agent E: cobertura confirmada i import 3200.0€ dins del llindar; s'aprova el PAGAMENT de ...€.

>>> DECISIÓ: PAGO   (HITL: False)
```

La traza muestra el razonamiento de cada agente en el orden en que intervinierol en el grafo LangGraph: G (antifrau) → B (validación documental) → C (extracción multimodal) → D (verificación de póliza) → E (resolución).

> **Sin MariaDB:** la CLI imprime un aviso de log del tipo `WARNING: No s'han pogut persistir les decisions de DEMO-PAGO: ...` pero continúa procesando todos los expedientes. La lógica agéntica es independiente de la persistencia.

---

## 7. Interpretación de resultados

### 7.1 Decisiones posibles

| Decisión | Significado | `hitl_required` | Estado en BD |
|---|---|---|---|
| `PAGO` | Expediente aprobado. El importe se procesa de forma autónoma (mock de transferencia). | `false` | `resolved` |
| `RECHAZO` | Expediente rechazado por ausencia de cobertura en póliza. Se envía notificación al cliente (mock). | `false` | `rejected` |
| `REVISIÓN_HUMANA` | El expediente supera el umbral de importe (`HITL_AMOUNT_THRESHOLD`) o el agente G detecta indicios de fraude. Un operador humano debe intervenir. | `true` | `pending_review` |
| `SOLICITUD_INFO` | El agente B detecta documentación incompleta. El expediente queda abierto hasta recibir los documentos que faltan. | `false` | `open` |

### 7.2 El campo `hitl_required`

El campo booleano `hitl_required` en la respuesta indica de forma explícita si el expediente ha sido derivado a revisión humana. Se activa en dos situaciones:

1. **Por importe elevado:** el Agent E compara `amount_requested` con `HITL_AMOUNT_THRESHOLD` (5.000 € por defecto). Si el importe supera el umbral, la decisión es `REVISIÓN_HUMANA` con `hitl_required: true`.
2. **Por riesgo de fraude:** el Agent G evalúa el expediente. Si la puntuación de riesgo supera el umbral interno del mock (`is_flagged: true`), el orquestrador deriva el expediente directamente al nodo HITL, ignorando el resto de la cadena de agentes.

El diseño de Human-in-the-Loop responde a los principios de IA responsable recogidos en la literatura sobre sistemas agénticos (Russell, 2019; Amershi et al., 2019): ningún pago de alto valor ni ningún caso con indicios de fraude se resuelve de forma totalmente autónoma.

### 7.3 El campo `reasoning_trace` — Chain of Thought

`reasoning_trace` es una lista de cadenas en la que cada elemento corresponde al razonamiento del agente que ejecutó el paso decisivo final. En la respuesta de la API solo se incluye la traza del último nodo ejecutado; la traza completa de todos los agentes queda persistida en la tabla `agent_decisions` de MariaDB (columna `reasoning`).

El Chain of Thought visible permite al evaluador:

- Verificar qué agente tomó la decisión y con qué argumento.
- Comprobar si el razonamiento proviene del LLM (texto más elaborado) o del fallback determinista (texto más esquemático).
- Detectar el motivo exacto de un rechazo o de una solicitud de información.

---

## 8. Inspección de la base de datos con Adminer

### 8.1 Acceso a Adminer

Con el sistema Docker levantado, abrir en el navegador:

```
http://localhost:8082
```

Adminer es una herramienta web ligera de administración de bases de datos (Vrána, 2024). En la pantalla de inicio, introducir los siguientes datos de conexión (idénticos a los del `.env.example`):

| Campo | Valor |
|---|---|
| Sistema | MariaDB |
| Servidor | `mariadb` |
| Usuario | `claims_user` |
| Contraseña | `claims_s3cret_dev` (o el valor configurado en `.env`) |
| Base de datos | `smart_claims` |

### 8.2 Tablas del esquema

La base de datos `smart_claims` contiene tres tablas:

| Tabla | Descripción |
|---|---|
| `claims` | Un registro por expediente procesado. Columnas principales: `id`, `client_id`, `claim_type`, `channel`, `status`, `amount_requested`, `amount_approved`, `created_at`. |
| `agent_decisions` | Una fila por decisión registrada por cada agente. Columnas: `claim_id` (FK), `agent`, `action`, `reasoning` (texto completo del CoT), `confidence`, `hitl_required`, `created_at`. |
| `hitl_feedback` | Tabla preparada para el feedback del operador humano en casos HITL. Columnas: `claim_id`, `decision_id` (FK), `reviewer`, `original_action`, `final_action`, `override_reason`. Vacía en el MVP actual (se alimentará en la siguiente fase). |

### 8.3 Consultar la traza de decisiones de un expediente

Para ver el ciclo completo de un expediente (por ejemplo, `CLM-PAGO-01`), ejecutar la siguiente consulta SQL desde la opción **"Ejecutar SQL"** de Adminer:

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
ORDER BY ad.created_at ASC;
```

El resultado muestra la secuencia cronológica de todos los agentes que intervinieron, con su razonamiento completo y si cada uno de ellos marcó el paso como requiriente de revisión humana.

Para ver el estado final del expediente:

```sql
SELECT id, claim_type, status, amount_requested, amount_approved, created_at
FROM claims
WHERE id = 'CLM-PAGO-01';
```

La base de datos incluye tres expedientes de seed preinsertados por `backend/db/init.sql` (`CLM-001`, `CLM-002`, `CLM-003`) que pueden usarse para verificar la inicialización del esquema.

---

## 9. Resolución de problemas frecuentes

### 9.1 Sin `ANTHROPIC_API_KEY` — el sistema usa el fallback

**Síntoma:** el razonamiento en `reasoning_trace` es breve y esquemático (p. ej., _"Agent E: cobertura confirmada i import 3200.0€ dins del llindar; s'aprova el PAGAMENT de ...€."_).

**Causa:** la variable `ANTHROPIC_API_KEY` no está configurada o es inválida. El módulo `reasoning.py` cae al texto de fallback predefinido.

**Solución:** si se desea el razonamiento enriquecido con el LLM, añadir una clave válida de Anthropic en `.env` y reiniciar los contenedores:

```bash
docker compose restart backend
```

El comportamiento de la demo es correcto en cualquier caso; el fallback es un comportamiento esperado del diseño.

### 9.2 Sin MariaDB — la CLI muestra un aviso pero continúa

**Síntoma al usar la CLI:** aparece en los logs una línea similar a:
```
WARNING  root: No s'han pogut persistir les decisions de DEMO-PAGO: ...
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
# Identificar proceso en el puerto 8000
netstat -ano | findstr :8000
# Detener el proceso (sustituir PID)
taskkill /PID <PID> /F
```

Alternativamente, modificar el mapeo de puertos en `docker-compose.yml` (columna izquierda del par `"host:contenedor"`).

### 9.4 El backend no arranca (`sca-backend` en estado `restarting`)

**Causa más frecuente:** MariaDB no ha completado su inicialización antes de que el backend intente conectarse.

**Solución:** esperar entre 30 y 60 segundos y verificar de nuevo:

```bash
docker compose ps
docker compose logs backend --tail=30
```

El healthcheck de MariaDB reintenta la conexión hasta 5 veces con intervalos de 10 s. Si el problema persiste, verificar que las variables `DB_*` en `.env` son consistentes con las definidas en el bloque `mariadb` de `docker-compose.yml`.

### 9.5 Error `404 Not Found` en `GET /api/v1/claims/{id}`

**Causa:** el expediente con ese identificador no existe en la base de datos. Los expedientes solo se persisten si el sistema Docker está levantado y la conexión a MariaDB es correcta. La CLI de demostración no persiste resultados.

**Solución:** enviar primero el expediente mediante `POST /api/v1/claims` con el sistema Docker activo, y consultar inmediatamente después con el mismo `claim_id`.

---

## 10. Referencias

Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., y Horvitz, E. (2019). Software engineering for machine learning: A case study. *Proceedings of the 41st International Conference on Software Engineering: Software Engineering in Practice*, 291–300. https://doi.org/10.1109/ICSE-SEIP.2019.00042

Anthropic. (2024). *Claude API documentation*. https://docs.anthropic.com

FastAPI. (2024). *FastAPI documentation: Interactive API docs*. https://fastapi.tiangolo.com/features/

Russell, S. (2019). *Human compatible: Artificial intelligence and the problem of control*. Viking.

Vrána, J. (2024). *Adminer — Database management in a single PHP file*. https://www.adminer.org
