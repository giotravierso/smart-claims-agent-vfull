---
name: project-context
description: Smart-Claims Agent TFM — alcance real del MVP, empresa real, sin APIs externas, entrega = arquitectura
metadata:
  type: project
---

Smart-Claims Agent es el MVP de un TFM (Máster ML/IA, OBS Business School) para Seguros Pepín.

Hechos que CORRIGEN la documentación del repo:
- **Seguros Pepín es una empresa REAL**, no ficticia (el README/CONTEXT_TFM la llaman "ficticia" — está desactualizado).
- **No habrá acceso a las APIs de sus sistemas reales** → las integraciones externas (pagos, notificaciones, core asegurador, OFAC) se quedan como mocks/simuladas. Esto es definitivo, no temporal.
- **El entregable es la ARQUITECTURA**, no el producto. La UX/frontend NO es prioritaria ahora mismo.
- Objetivo del MVP: que el **proceso end-to-end se pueda ejecutar y sirva/demuestre valor** (con mocks para lo externo).

**Why:** El repo se documentó como si la empresa fuera ficticia y como si todo estuviera "operativo", pero el código es un esqueleto. El usuario aclara qué importa de verdad para la entrega.

**How to apply:** No invertir esfuerzo en frontend/UX. Priorizar que el flujo agéntico (orquestador A + agentes B–G + RAG + persistencia de decisiones) se ejecute de extremo a extremo con las mock tools. Mantener las integraciones externas como simuladas.

**Entrega 2 (deadline 26/06/2026)** — el núcleo es la MEMORIA escrita, tres apartados: (1) Arquitectura, (2) Herramientas, (3) Manual de usuario. Adicionalmente se continúa el prototipo y se pueden adelantar/revisar apartados de entregas previas. Es decir: el documento pesa más que el código en esta entrega. Normativa: APA 7.ª, en castellano.
