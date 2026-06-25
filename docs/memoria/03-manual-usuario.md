# Manual de usuario — Smart-Claims Agent

**Seguros Pepín, S.A. — MVP agéntico de gestión de siniestros**  
TFM Máster en Machine Learning e Inteligencia Artificial, OBS Business School

---

## Índice

1. [Introducción y público objetivo](#1-introducción-y-público-objetivo)
2. [Requisitos previos](#2-requisitos-previos)
3. [Configuración del entorno](#3-configuración-del-entorno)
4. [Modo 1 — Docker Compose (arquitectura completa)](#4-modo-1--docker-compose-arquitectura-completa)
5. [Modo 2 — App Streamlit (demo principal)](#5-modo-2--app-streamlit-demo-principal)
6. [Modo 3 — CLI de demostración y API REST](#6-modo-3--cli-de-demostración-y-api-rest)
7. [Interpretación de resultados](#7-interpretación-de-resultados)
8. [Inspección de la base de datos con Adminer](#8-inspección-de-la-base-de-datos-con-adminer)
9. [Resolución de problemas frecuentes](#9-resolución-de-problemas-frecuentes)
10. [Referencias](#10-referencias)

---

## 1. Introducción y público objetivo

Este manual describe el modo de operación del prototipo **Smart-Claims Agent** en su versión de entrega del TFM. No es un manual orientado al empleado final de Seguros Pepín, S.A., sino un **manual operativo para el evaluador técnico** (director del TFM, tribunal académico o desarrollador que revise el prototipo). Su objetivo es permitir reproducir, inspeccionar y validar el comportamiento del sistema de forma autónoma.

El sistema puede operarse de tres formas complementarias:

- **Modo 1 — Docker Compose:** levanta los cinco servicios del prototipo (backend FastAPI, frontend Streamlit, ChromaDB, MariaDB y Adminer) en contenedores aislados, con persistencia real en base de datos.
- **Modo 2 — App Streamlit (la demo principal):** interfaz web autónoma que invoca el grafo de agentes directamente en el mismo proceso Python, sin necesidad de Docker ni de MariaDB. Es la modalidad desplegada en Streamlit Community Cloud y la recomendada para la demostración en vivo ante el tribunal.
- **Modo 3 — CLI de demostración y API REST:** la CLI ejecuta cuatro casos predefinidos desde línea de comandos y muestra el Chain of Thought; la API REST acepta peticiones HTTP desde curl, Postman o cualquier cliente.

> **Nota sobre integraciones externas:** todas las herramientas que en producción consultarían sistemas reales de Seguros Pepín (motor antifraude OFAC, gestor documental, núcleo de pólizas, sistemas de pago) están implementadas como mocks deterministas o sobre datos reales de la empresa embebidos en ChromaDB. El LLM Claude de Anthropic es **opcional**: si se proporciona `ANTHROPIC_API_KEY`, cada agente genera razonamientos Chain of Thought con el modelo `claude-sonnet-4-6` y el Agente C realiza extracción multimodal real de documentos subidos; sin clave, el sistema usa un fallback determinista y la demo funciona de forma idéntica en cuanto a decisiones.

---

## 2. Requisitos previos

### 2.1 Modo 1 — Docker Compose

| Requisito | Versión mínima | Notas |
|---|---|---|
| Docker Engine | 24.x | Incluye el demonio de contenedores |
| Docker Compose | v2 (plugin integrado) | Comando `docker compose` sin guion |
| RAM disponible | 4 GB | Para los cinco servicios en paralelo |
| Puertos libres | 8000, 8080, 8082, 8501, 3306 | Véase tabla de servicios en §4 |

Verificación rápida:

```bash
docker --version
docker compose version
```

### 2.2 Modo 2 — App Streamlit (local) y Modo 3 — CLI

| Requisito | Versión | Notas |
|---|---|---|
| Python | 3.11 | Versión recomendada; 3.12 también es compatible |
| Dependencias (raíz) | — | `requirements.txt` de la raíz del repositorio (para Streamlit) |
| Dependencias (backend) | — | `backend/requirements.txt` (para CLI y API) |

En Windows el lanzador oficial de Python es `py`:

```powershell
py --version
```

La app Streamlit y la CLI no requieren MariaDB ni ChromaDB para funcionar; si no están disponibles, el sistema lo detecta y activa el fallback con un aviso de log.

---

## 3. Configuración del entorno

### 3.1 Crear el fichero `.env`

El fichero `.env` es la fuente de configuración del sistema. Se parte de la plantilla incluida en el repositorio:

```bash
# Bash (Linux / macOS)
cp .env.example .env
```

```powershell
# PowerShell (Windows)
Copy-Item .env.example .env
```

### 3.2 Variables de entorno relevantes

Editar `.env` con los valores adecuados. La tabla siguiente describe las variables más importantes tal como aparecen en `.env.example`:

| Variable | Valor por defecto en `.env.example` | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-XXXX...` (placeholder) | Clave API de Anthropic. **Opcional** — véase §3.3 |
| `HITL_AMOUNT_THRESHOLD` | `5000.0` | Umbral (€) por encima del cual se activa la revisión humana (HITL) |
| `SCA_RAG_ENABLED` | `1` | `1` = el Agente D usa RAG real sobre ChromaDB; vacío o `0` = catálogo determinista |
| `DB_USER` | `claims_user` | Usuario de aplicación de MariaDB |
| `DB_PASSWORD` | `claims_s3cret_dev` | Contraseña del usuario de aplicación |
| `DB_HOST` | `mariadb` | Hostname del servicio MariaDB (nombre del contenedor en Docker) |
| `DB_PORT` | `3306` | Puerto de MariaDB |
| `DB_NAME` | `smart_claims` | Nombre de la base de datos |
| `DB_ROOT_PASSWORD` | `root_s3cret_dev` | Contraseña root de MariaDB |
| `CHROMA_HOST` | `chromadb` | Hostname del servicio ChromaDB |
| `CHROMA_PORT` | `8000` | Puerto interno de ChromaDB |
| `CHROMA_COLLECTION` | `pepin_policies` | Colección vectorial con las pólizas de Seguros Pepín |
| `BACKEND_URL` | `http://backend:8000` | URL interna del backend (entre contenedores Docker) |
| `ENVIRONMENT` | `development` | Entorno de ejecución |
| `LOG_LEVEL` | `INFO` | Nivel de log del backend |

> **Nota sobre moneda:** los importes se expresan en euros (€) como simplificación del prototipo; en una implantación para Seguros Pepín se localizarían a pesos dominicanos (DOP / RD$).

### 3.3 La clave `ANTHROPIC_API_KEY` y el modo fallback

Esta variable controla el nivel de inteligencia real del sistema:

- **Con clave válida:** cada agente llama a `claude-sonnet-4-6` para generar el razonamiento Chain of Thought. El Agente C realiza extracción multimodal real (tipo, importe, fecha, resumen y confianza) sobre los documentos subidos mediante Claude Vision. Requiere conexión a internet y saldo en la cuenta de Anthropic.
- **Sin clave (o clave vacía):** el módulo de razonamiento detecta la ausencia de la variable y retorna texto de fallback predefinido. **La decisión final del orquestador es idéntica en ambos modos**, ya que la lógica de enrutamiento es determinista (basada en cobertura, importe y documentos aportados). Para la evaluación académica del prototipo, el modo fallback es suficiente.

La app Streamlit muestra en la barra lateral el indicador de modo activo:

- `Claude activo (CoT enriquecido)` — con clave.
- `Modo fallback determinista (sin clave)` — sin clave.

> En Streamlit Community Cloud, la clave se inyecta vía la sección *Secrets* del panel de administración de la app (véase `docs/DEPLOY-STREAMLIT.md`), nunca como variable de entorno del repositorio.

### 3.4 Variable `SCA_RAG_ENABLED` y el Agente D

Cuando `SCA_RAG_ENABLED=1`, el Agente D (Verificación de cobertura) consulta ChromaDB para recuperar el fragmento de póliza más relevante según el tipo de siniestro. Si ChromaDB no está disponible o la variable está vacía/a `0`, el agente cae automáticamente al catálogo determinista sin interrumpir el flujo.

La app Streamlit activa `SCA_RAG_ENABLED=1` por defecto mediante `os.environ.setdefault("SCA_RAG_ENABLED", "1")` al arrancar.

---

## 4. Modo 1 — Docker Compose (arquitectura completa)

### 4.1 Arranque del sistema

Desde la **raíz del repositorio**, con el fichero `.env` configurado:

```bash
docker compose up -d --build
```

Docker Compose construye las imágenes locales del backend y el frontend, descarga el resto de imágenes (`chromadb/chroma:0.5.3`, `mariadb:11.3`, `adminer:4.8.1`) y levanta todos los servicios en segundo plano. El primer arranque puede tardar entre 2 y 5 minutos.

Para seguir los logs del backend en tiempo real:

```bash
docker compose logs -f backend
```

### 4.2 Servicios y URLs

| Servicio | Contenedor | Puerto host | URL | Descripción |
|---|---|---|---|---|
| Backend FastAPI | `sca-backend` | 8000 | `http://localhost:8000` | API REST + orquestador LangGraph |
| Frontend Streamlit | `sca-frontend` | 8501 | `http://localhost:8501` | Dashboard (versión con API) |
| ChromaDB | `sca-chromadb` | 8080 | `http://localhost:8080` | Vector store para RAG de pólizas |
| MariaDB | `sca-mariadb` | 3306 | `localhost:3306` | Persistencia relacional |
| Adminer | `sca-adminer` | 8082 | `http://localhost:8082` | Inspector web de la BD |

> El contenedor `sca-backend` espera a que MariaDB supere su healthcheck antes de iniciarse (condición `service_healthy` en `docker-compose.yml`). Si el backend aparece como `restarting` en los primeros 30-60 segundos, es comportamiento normal.

### 4.3 Verificación del sistema

Verificar que el backend responde:

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{"status": "ok", "version": "0.5.0"}
```

Consultar el estado de los seis agentes:

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

La documentación Swagger interactiva está disponible en `http://localhost:8000/docs`.

### 4.4 Parada del sistema

```bash
# Detener los contenedores (conserva los volúmenes de datos)
docker compose down

# Detener y eliminar también los volúmenes
docker compose down -v
```

---

## 5. Modo 2 — App Streamlit (demo principal)

La app Streamlit (`streamlit_app.py`) es la **interfaz principal para la demostración**. Invoca el grafo de agentes directamente en el mismo proceso Python, sin backend FastAPI ni MariaDB. Está disponible como demo en vivo en Streamlit Community Cloud y también puede ejecutarse en local.

### 5.1 Arranque en local

Desde la **raíz del repositorio**:

```powershell
# Windows
py -m streamlit run streamlit_app.py
```

```bash
# Linux / macOS
python3.11 -m streamlit run streamlit_app.py
```

La app abre automáticamente en el navegador en `http://localhost:8501`.

Para el despliegue en Streamlit Community Cloud, consultar `docs/DEPLOY-STREAMLIT.md` (repositorio `FreeBarnOwl/smart-claims-agent-vfull`, rama `main`, fichero principal `streamlit_app.py`).

### 5.2 Estructura de la interfaz

La app tiene una cabecera de marca Seguros Pepín con estética Salesforce Lightning (azul corporativo `#0B4DA2`, acento naranja `#F39200`) y una barra de navegación lateral con cuatro secciones:

| Sección | Descripción |
|---|---|
| **Inicio** | Pantalla de bienvenida con accesos directos a las cuatro acciones principales |
| **Nueva reclamación** | Formulario completo + escenarios rápidos de un clic |
| **Historial** | Tabla resumen de todos los expedientes procesados en la sesión y gráfico de distribución por decisión |
| **Arquitectura** | Descripción del patrón Supervisor (Hub-and-Spoke), los seis agentes y las características clave del sistema |

La barra lateral también muestra el indicador de modo LLM (Claude activo vs. fallback determinista).

### 5.3 Crear una reclamación: escenarios rápidos

En la vista **Nueva reclamación**, la sección superior muestra cuatro botones de escenario rápido, uno por cada camino principal del flujo:

| Botón | `claim_type` | Importe | Documentos | Decisión esperada |
|---|---|---|---|---|
| Pago automático | `danys_propis` | 2.500 € | Completos | `PAGO` |
| Revisión humana (HITL) | `responsabilitat` | 9.500 € | Completos | `REVISION_HUMANA` |
| Información requerida | `danys_propis` | 3.000 € | Solo `factura` | `INFO_REQUERIDA` |
| Rechazo por no cobertura | `danys_mecanics` | 1.500 € | Completos | `RECHAZO` |

Al pulsar **Procesar** en cualquiera de ellos, el expediente se envía directamente al orquestador y el resultado aparece debajo del formulario.

### 5.4 Crear una reclamación: formulario personalizado

El formulario personalizado permite ajustar todos los parámetros del expediente:

| Campo | Descripción |
|---|---|
| **Nombre del asegurado** | Se compara contra la lista sintética OFAC en el Agente G. Valor por defecto: `Juan García`. |
| **ID Cliente** | Identificador del asegurado. Valor por defecto: `CLIENT-A`. |
| **Email del cliente** | Dirección de notificaciones. |
| **Tipo de siniestro** | Selector con los cuatro tipos disponibles (véase §5.6). |
| **Importe reclamado (€)** | Campo numérico de 0 a 100.000 €, paso de 100 €. |
| **Documentos aportados (tipo)** | Selector múltiple con los documentos requeridos para el tipo elegido. Deseleccionar alguno simula documentación incompleta y provoca `INFO_REQUERIDA`. |
| **Sube los documentos reales** | `file_uploader` que acepta PNG, JPG, JPEG, WEBP y PDF. Los ficheros subidos son procesados por el **Agente C con Claude Vision** (requiere `ANTHROPIC_API_KEY`). |

Pulsar **Procesar reclamación** envía el expediente al orquestador. Los ficheros subidos se convierten en la estructura que espera el Agente C: nombre, tipo MIME, bytes y tipo de documento (`auto`).

### 5.5 Cómo disparar cada uno de los cinco caminos del flujo

#### Camino 1: PAGO automático

- Tipo: `Daños propios`
- Importe: cualquier valor hasta 5.000 € (o el umbral configurado en `HITL_AMOUNT_THRESHOLD`)
- Documentos: seleccionar todos (`foto_danys`, `factura`, `denuncia_companyia`)
- Nombre: cualquiera que no figure en la lista OFAC

#### Camino 2: REVISION_HUMANA por importe elevado

- Tipo: `Responsabilidad civil` (o cualquier tipo cubierto)
- Importe: superior a 5.000 € (p. ej., 9.500 €)
- Documentos: completos
- El Agente E detecta que el importe supera el umbral HITL y deriva el expediente a revisión humana.

#### Camino 3: RECHAZO por falta de cobertura

- Tipo: `Daños mecánicos`
- Importe y documentos: cualquier valor
- El Agente D determina que `danys_mecanics` está excluido de la póliza (exclusión SP-PCS-009 § 7.3) y el Agente E emite el rechazo.

#### Camino 4: INFO_REQUERIDA por documentación incompleta

- Tipo: cualquier tipo cubierto (p. ej., `Daños propios`)
- Documentos: deseleccionar uno o más de los requeridos (p. ej., dejar solo `factura`)
- El Agente B detecta los documentos faltantes y el flujo se detiene con `INFO_REQUERIDA`.

#### Camino 5: BLOQUEO por fraude / coincidencia OFAC

- En el campo **Nombre del asegurado**, introducir un nombre presente en la lista sintética OFAC que usa el Agente G, por ejemplo:

  ```
  Viktor Nikolaev Kozlov
  ```

- El Agente G realiza una comparación difusa (fuzzy matching) entre el nombre introducido y la lista de sanciones. Si la similitud supera el umbral, emite veredicto `BLOCKED` y el orquestador termina el flujo con decisión `RECHAZO_FRAUDE`.

### 5.6 Tipos de siniestro disponibles

| Clave interna | Etiqueta en el formulario | Cobertura | Documentos requeridos |
|---|---|---|---|
| `danys_propis` | Daños propios | Cubierto | `foto_danys`, `factura`, `denuncia_companyia` |
| `responsabilitat` | Responsabilidad civil | Cubierto | `foto_danys`, `acta_policial`, `dades_tercer` |
| `robatori` | Robo | Cubierto | `acta_policial`, `llista_objectes_robats` |
| `danys_mecanics` | Daños mecánicos | **Excluido** | `informe_taller`, `factura` |

### 5.7 Lectura del resultado

Una vez procesado el expediente, la app muestra el resultado en varias secciones:

**Cabecera del expediente**

- Identificador generado automáticamente (formato `CLM-XXXXXXXX`).
- Pastilla de color con la decisión: verde (`PAGO`), rojo (`RECHAZO` / `RECHAZO_FRAUDE`), naranja (`REVISION_HUMANA`), azul (`INFO_REQUERIDA`).
- Causa de terminación del flujo (`termination_reason`).

**Métricas principales** (cuatro tarjetas)

- Estado del expediente (`resolved`, `rejected`, `pending_review`, `validating`).
- Decisión final.
- Importe pagado vs. importe solicitado.
- Tiempo de procesamiento en segundos.

**Cribado antifraude (Agente G)**

- Veredicto: `CLEAR` (verde), `MEDIUM_RISK` (amarillo), `HIGH_RISK` (naranja) o `BLOCKED` (rojo, coincidencia OFAC).
- Score de riesgo numérico entre 0 y 1.

**Cobertura (Agente D · RAG sobre pólizas)**

- Visible solo cuando `SCA_RAG_ENABLED=1` y ChromaDB está disponible.
- Indica la sección de póliza recuperada y muestra el fragmento de texto extraído de los documentos de Seguros Pepín.

**Extracción multimodal real (Agente C · Claude Vision)**

- Visible solo cuando se han subido ficheros y `ANTHROPIC_API_KEY` está configurada.
- Por cada documento subido: tipo de documento, importe leído, fecha, nivel de confianza y resumen textual generado por Claude.

**Cadena de razonamiento de los agentes (Chain of Thought)**

- Timeline con una tarjeta por cada agente que intervino en el flujo.
- Muestra el nombre del agente, la acción realizada y el razonamiento completo.
- El orden de intervención es: A (triaje) → B (validación documental) → C (extracción multimodal) → G (fraude/cumplimiento) → D (cobertura) → E (resolución).

---

## 6. Modo 3 — CLI de demostración y API REST

### 6.1 CLI de demostración

La CLI ejecuta cuatro expedientes predefinidos directamente sobre el orquestador Python y muestra el Chain of Thought y la decisión en la terminal. No requiere Docker, MariaDB ni ChromaDB.

#### Instalación de dependencias (una sola vez)

```powershell
# Windows — desde la raíz del repositorio
py -m pip install -r backend/requirements.txt
```

```bash
# Linux / macOS
python3.11 -m pip install -r backend/requirements.txt
```

#### Ejecución

```powershell
# Windows — desde la raíz del repositorio
py backend/scripts/run_demo.py
```

```bash
# Linux / macOS
python3.11 backend/scripts/run_demo.py
```

O desde el contenedor del backend (si Docker está levantado):

```bash
docker exec -it sca-backend python scripts/run_demo.py
```

#### Casos de demostración

El script ejecuta cuatro expedientes con una semilla aleatoria fija (`random.seed(7)`) para garantizar reproducibilidad:

| Expediente | `claim_type` | Importe | Documentos | Decisión esperada |
|---|---|---|---|---|
| `DEMO-PAGO` | `danys_propis` | 3.200 € | Completos | `PAGO` |
| `DEMO-HITL` | `responsabilitat` | 8.500 € | Completos | `REVISION_HUMANA` |
| `DEMO-RECHAZO` | `danys_mecanics` | 1.000 € | Completos | `RECHAZO` |
| `DEMO-INFO` | `danys_propis` | 1.000 € | Solo `factura` | `INFO_REQUERIDA` |

> Cada caso aplica su propia semilla aleatoria antes de invocar al orquestador, de forma que los resultados son independientes del orden de ejecución.

#### Ejemplo de salida

```
------------------------------------------------------------------------------
  Expediente: DEMO-PAGO
  Escenario:  Pago automatico (cobertura + importe bajo)
  Tipo:       danys_propis  |  Importe: 3200.0 EUR
------------------------------------------------------------------------------

  Razonamiento (Chain of Thought):
    1. Agente A: expediente DEMO-PAGO de tipo 'danys_propis' por importe 3200.0 EUR...
    2. Agente B: documentación completa y conforme.
    3. Agente C: extraídos 3 documentos con confianza media 0.91.
    4. Agente G: riesgo de fraude 0.12, sin indicios relevantes.
    5. Agente D: siniestro 'danys_propis' cubierto según SP-PCS-009 § 3.2.
    6. Agente E: cobertura confirmada y 2900.00 EUR dentro del umbral; PAGO aprobado.

  >>> Decision:  PAGO
      Estado:    resolved
      HITL:      False
      Importe pagado: 2900.0 EUR
```

El importe pagado (2.900 €) corresponde a los 3.200 € reclamados menos la franquicia de 300 € de la póliza de daños propios.

### 6.2 API REST

Con el backend levantado (Docker o ejecución local), la API REST acepta peticiones en `http://localhost:8000`.

#### Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Estado del servicio (`{"status":"ok","version":"0.5.0"}`) |
| `GET` | `/api/v1/agents/status` | Estado y descripción de los seis agentes |
| `POST` | `/api/v1/claims/` | Procesa un expediente → decisión + CoT + HITL |
| `GET` | `/api/v1/claims/` | Lista expedientes (paginación y filtro por estado) |
| `GET` | `/api/v1/claims/{claim_id}` | Detalle de un expediente con todas sus decisiones |
| `GET` | `/api/v1/claims/{claim_id}/trace` | Solo el Chain of Thought de un expediente |

La documentación Swagger interactiva está en `http://localhost:8000/docs`.

#### Ejemplo 1: PAGO (daños propios, importe bajo, docs completos)

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-PAGO-01",
    "client_id": "C-A",
    "claim_type": "danys_propis",
    "channel": "email",
    "amount_requested": 3200.0,
    "documents": ["foto_danys", "factura", "denuncia_companyia"]
  }'
```

Respuesta esperada (resumen):

```json
{
  "claim_id": "CLM-PAGO-01",
  "status": "resolved",
  "decision": "PAGO",
  "amount_paid": 2900.0,
  "hitl_required": false
}
```

#### Ejemplo 2: REVISION_HUMANA (importe supera el umbral HITL)

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-HITL-01",
    "client_id": "C-B",
    "claim_type": "responsabilitat",
    "channel": "web",
    "amount_requested": 8500.0,
    "documents": ["foto_danys", "acta_policial", "dades_tercer"]
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

#### Ejemplo 3: RECHAZO (tipo sin cobertura)

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-RECH-01",
    "client_id": "C-C",
    "claim_type": "danys_mecanics",
    "channel": "email",
    "amount_requested": 1000.0,
    "documents": ["informe_taller", "factura"]
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

#### Ejemplo 4: INFO_REQUERIDA (documentación incompleta)

```bash
curl -s -X POST http://localhost:8000/api/v1/claims/ \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "CLM-INFO-01",
    "client_id": "C-D",
    "claim_type": "danys_propis",
    "channel": "email",
    "amount_requested": 1000.0,
    "documents": ["factura"]
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

#### Consultar un expediente ya procesado

```bash
curl -s http://localhost:8000/api/v1/claims/CLM-PAGO-01
```

Si el expediente no existe en la base de datos, la respuesta es `HTTP 404`.

---

## 7. Interpretación de resultados

### 7.1 Decisiones posibles

| Decisión | Significado | `hitl_required` | Estado (`status`) |
|---|---|---|---|
| `PAGO` | Expediente aprobado. Pago procesado de forma autónoma (mock de transferencia). | `false` | `resolved` |
| `RECHAZO` | Expediente rechazado por ausencia de cobertura en póliza. Se emite notificación al cliente (mock). | `false` | `rejected` |
| `RECHAZO_FRAUDE` | Expediente bloqueado por el cribado antifraude: el Agente G emitió veredicto `HIGH_RISK` o `BLOCKED`. | `false` | `rejected` |
| `REVISION_HUMANA` | El importe supera `HITL_AMOUNT_THRESHOLD` (5.000 € por defecto). Un operador humano debe revisar el expediente. | `true` | `pending_review` |
| `INFO_REQUERIDA` | Documentación incompleta. El expediente queda en espera de los documentos pendientes. | `false` | `validating` |

### 7.2 Human-in-the-Loop (HITL) y el campo `hitl_required`

El campo booleano `hitl_required` indica de forma explícita si el expediente requiere intervención humana. Se activa cuando la decisión es `REVISION_HUMANA`, es decir, cuando el importe supera el umbral configurado en `HITL_AMOUNT_THRESHOLD`. El diseño garantiza que ningún pago de alto valor se resuelve de forma totalmente autónoma, conforme a los principios de IA responsable.

El umbral es configurable sin necesidad de recompilar el código: basta con cambiar el valor de `HITL_AMOUNT_THRESHOLD` en `.env` y reiniciar el servicio.

### 7.3 Veredicto de fraude (Agente G)

El Agente G actúa como gate de cumplimiento tras la recepción documental (validación y extracción) y antes de la resolución, de modo que sus cuatro detectores —incluida la coherencia documental— disponen de los datos extraídos. Su motor antifraude combina cuatro detectores:

1. **OFAC fuzzy:** comparación difusa entre el nombre del asegurado y la lista sintética de sanciones.
2. **Importe anómalo:** detección por Z-score sobre el histórico de importes.
3. **Duplicados:** comprobación de expedientes previos del mismo cliente.
4. **Coherencia documental:** coherencia temporal entre las fechas de los documentos (p. ej. que la factura no sea anterior al siniestro).

El resultado del Agente G incluye un `verdict` graduado (`CLEAR`, `MEDIUM_RISK`, `HIGH_RISK` o `BLOCKED`), un `risk_score` numérico entre 0 y 1, y el indicador `is_flagged`. El expediente se marca (`is_flagged=True`) y el orquestador termina el flujo con `RECHAZO_FRAUDE` solo si el veredicto es `HIGH_RISK` o `BLOCKED` (este último para coincidencia OFAC); en ese caso no se invocan los agentes D ni E (la validación B y la extracción C ya se han ejecutado antes).

### 7.4 Cobertura RAG (Agente D)

Cuando `SCA_RAG_ENABLED=1`, el campo `coverage_result` de la respuesta incluye:

- `source: "rag"` — indica que la cobertura se determinó mediante recuperación vectorial sobre ChromaDB.
- `policy_section` — identificador de la sección de póliza recuperada.
- `retrieved_snippet` — fragmento de texto del documento de póliza de Seguros Pepín.

Sin RAG, `source` es `"mock"` y la cobertura se determina por el catálogo determinista.

### 7.5 Extracción multimodal (Agente C · Claude Vision)

Cuando se suben documentos reales y `ANTHROPIC_API_KEY` está configurada, el campo `extraction_result` incluye:

- `source: "claude_vision"` — indica extracción real por LLM.
- `by_document` — diccionario con una entrada por fichero subido, con los campos:
  - `doc_type` — tipo de documento identificado por Claude.
  - `amount` — importe leído del documento.
  - `date` — fecha leída del documento.
  - `confidence` — nivel de confianza entre 0 y 1.
  - `summary` — resumen textual del contenido del documento.

> El importe de la decisión final es siempre el introducido en el formulario; la extracción multimodal se presenta como información complementaria para el agente resolutor y el operador humano.

### 7.6 Chain of Thought (`reasoning_trace` / `decisions_log`)

La cadena de razonamiento se presenta como una timeline con una tarjeta por agente. Permite al evaluador:

- Verificar qué agentes intervinieron y en qué orden.
- Comprobar si el razonamiento proviene del LLM (texto elaborado, con Markdown) o del fallback determinista (texto esquemático).
- Identificar el motivo exacto de un rechazo, una solicitud de información o una derivación a HITL.

La traza de un expediente persistido en BD puede consultarse también vía `GET /api/v1/claims/{id}/trace`.

---

## 8. Inspección de la base de datos con Adminer

### 8.1 Acceso a Adminer

Con el sistema Docker levantado, abrir en el navegador:

```
http://localhost:8082
```

Introducir los siguientes datos de conexión:

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
| `claims` | Un registro por expediente. Columnas principales: `id`, `client_id`, `claim_type`, `channel`, `status`, `amount_requested`, `amount_approved`, `created_at`. |
| `agent_decisions` | Una fila por decisión de cada agente. Columnas: `claim_id` (FK), `agent`, `action`, `reasoning` (texto completo del CoT), `confidence`, `hitl_required`, `created_at`. |
| `hitl_feedback` | Preparada para registrar el feedback del operador humano en casos HITL. Columnas: `claim_id`, `decision_id` (FK), `reviewer`, `original_action`, `final_action`, `override_reason`. En el MVP actual está vacía; se alimentará en fases posteriores. |

### 8.3 Consultas SQL útiles

**Traza completa de decisiones de un expediente:**

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

**Estado final de un expediente:**

```sql
SELECT id, claim_type, status, amount_requested, amount_approved, created_at
FROM claims
WHERE id = 'CLM-PAGO-01';
```

**Resumen de expedientes por estado:**

```sql
SELECT status, COUNT(*) AS total
FROM claims
GROUP BY status
ORDER BY total DESC;
```

---

## 9. Resolución de problemas frecuentes

### 9.1 Sin `ANTHROPIC_API_KEY` — el sistema usa el fallback determinista

**Síntoma:** el razonamiento en `reasoning_trace` es breve y esquemático. En la barra lateral de la app Streamlit aparece el indicador `Modo fallback determinista (sin clave)`.

**Causa:** la variable `ANTHROPIC_API_KEY` no está configurada o es inválida.

**Solución:** añadir una clave válida de Anthropic en `.env` y reiniciar:

```bash
docker compose restart backend
```

O, en la app Streamlit local, añadir la clave en `.env` antes de lanzar `streamlit run`. En Streamlit Cloud, añadir la clave en la sección *Secrets* del panel de administración (clave `ANTHROPIC_API_KEY`).

El comportamiento de la demo es correcto en cualquier caso; el fallback es un comportamiento previsto del diseño.

### 9.2 Sin MariaDB — la CLI muestra un aviso pero continúa

**Síntoma (CLI):** aparece una línea de log similar a:

```
WARNING root: No se han podido persistir las decisiones de DEMO-PAGO: ...
```

**Causa:** la CLI se ejecuta sin el servicio MariaDB levantado. `process_claim` captura la excepción en un bloque `try/except` y continúa el flujo sin interrupciones.

**Solución:** este comportamiento es intencional. Para persistencia completa, usar el despliegue Docker (§4).

### 9.3 Sin ChromaDB — el Agente D usa el catálogo determinista

**Síntoma:** en el resultado, `coverage_result.source` es `"mock"` en lugar de `"rag"`, aunque `SCA_RAG_ENABLED=1`.

**Causa:** ChromaDB no está disponible o la colección de pólizas no está indexada. El Agente D cae automáticamente al catálogo determinista.

**Solución:** en el despliegue Docker, verificar que el contenedor `sca-chromadb` está en estado `running`:

```bash
docker compose ps chromadb
```

Si el contenedor está parado, reiniciarlo:

```bash
docker compose start chromadb
```

### 9.4 Puerto ocupado al arrancar Docker

**Síntoma:** error al ejecutar `docker compose up -d`:

```
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8000 -> ...
```

**Causa:** uno de los puertos requeridos (8000, 8080, 8082, 8501 o 3306) está en uso.

**Solución en Windows:**

```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

Alternativamente, cambiar el mapeo de puertos en `docker-compose.yml` (columna izquierda del par `host:contenedor`).

### 9.5 El backend no arranca (`sca-backend` en estado `restarting`)

**Causa más frecuente:** MariaDB no ha completado su inicialización cuando el backend intenta conectarse. El `docker-compose.yml` ya define la condición `service_healthy` para el healthcheck de MariaDB, pero en equipos lentos puede necesitar más tiempo.

**Solución:** esperar entre 30 y 60 segundos y verificar:

```bash
docker compose ps
docker compose logs backend --tail=30
```

Si el problema persiste, comprobar que los valores `DB_*` en `.env` coinciden con los definidos en el bloque `mariadb` de `docker-compose.yml`.

### 9.6 Error `404 Not Found` al consultar `GET /api/v1/claims/{id}`

**Causa:** el expediente no existe en la base de datos. Esto ocurre cuando se usa la CLI sin MariaDB disponible, o cuando el `claim_id` de la consulta no coincide con el que usó `process_claim`.

**Solución:** enviar primero el expediente con `POST /api/v1/claims/` con el sistema Docker activo, y consultar inmediatamente después con el mismo `claim_id`.

### 9.7 El Agente G detecta fraude en un expediente legítimo de prueba

**Causa:** el mock de `check_fraud` incluye un componente aleatorio que, sin semilla fija, puede producir un `risk_score` elevado de forma inesperada.

**Solución para reproducibilidad:** usar la CLI de demostración (§6.1), que aplica `random.seed(7)` antes de cada caso, garantizando resultados consistentes entre ejecuciones.

### 9.8 `RuntimeError: Event loop is closed` al terminar la CLI

**Síntoma:** la CLI termina con un traceback cosmético:

```
Exception ignored in: <function Connection.__del__ ...>
RuntimeError: Event loop is closed
```

**Causa:** el driver `aiomysql` intenta cerrar sus conexiones después de que el bucle asíncrono se ha cerrado. No afecta al resultado del flujo; es un aviso puramente cosmético.

**Solución:** ignorar el aviso. El script `run_demo.py` ya incluye `await engine.dispose()` al final de `main()` para minimizar este comportamiento.

---

## 10. Referencias

Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., y Horvitz, E. (2019). Software engineering for machine learning: A case study. *Proceedings of the 41st International Conference on Software Engineering: Software Engineering in Practice*, 291–300. https://doi.org/10.1109/ICSE-SEIP.2019.00042

Anthropic. (2024). *Claude API documentation*. https://docs.anthropic.com

FastAPI. (2024). *FastAPI documentation: Interactive API docs*. https://fastapi.tiangolo.com/features/

Russell, S. (2021). *Human compatible: Artificial intelligence and the problem of control*. Viking.

Vrána, J. (2024). *Adminer — Database management in a single PHP file*. https://www.adminer.org
