# MEMORY — Smart-Claims Agent

Notas de contexto persistente para el equipo técnico del TFM. Este fichero recoge información de referencia frecuente que se reutiliza entre sesiones.

## Estado actual del proyecto (junio 2026)

- **Rama activa:** `solucion_final` en el repositorio `smart-claims-agent-vfull`.
- **Versión consolidada:** `v0.6.0-consolidated`.
- **Tests automatizados:** 25/25 pasando sobre SQLite en memoria.
- **Evaluación funcional:** precisión global del 96,7 % sobre 30 casos sintéticos.
- **Despliegue:** 5 servicios Docker operativos (`sca-backend`, `sca-frontend`, `sca-mariadb`, `sca-chromadb`, `sca-adminer`).
- **CLI de demostración:** 4 escenarios validados (`DEMO-PAGO`, `DEMO-HITL`, `DEMO-RECHAZO`, `DEMO-INFO`).

## Decisiones de diseño consolidadas

- Patrón **Supervisor (Hub-and-Spoke)** sobre LangGraph, con `supervisor_router()` como única función de enrutamiento.
- **6 agentes** organizados en torno al supervisor, cada uno en un fichero separado bajo `backend/app/agents/`.
- Estado compartido `ClaimState` con acumuladores `Annotated[list, operator.add]` para `reasoning_trace` y `decisions_log`.
- Razonamiento LLM **opcional**: helper `reason()` con *fallback* determinista si no hay `ANTHROPIC_API_KEY`.
- Persistencia centralizada en `process_claim`, envuelta en `try/except` (best-effort).
- Repository pattern en `db/repository.py` para todos los accesos a MariaDB.
- Mocks definitivos de todas las integraciones externas (no se dispone de APIs reales de Seguros Pepín).
- Marco normativo: **Ley 172-13** de la República Dominicana (no RGPD).
- Modelo LLM: **`claude-sonnet-4-6`** (no `claude-sonnet-4-20250514` ni otros nombres antiguos).
