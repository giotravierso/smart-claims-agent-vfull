<!-- PORTADA — rellenar los campos [entre corchetes] antes de generar el PDF -->

# Smart-Claims Agent
## Sistema Agéntico de Procesamiento Multimodal y Ejecución Autónoma para la Gestión de Siniestros

**Trabajo Fin de Máster — Entrega 2**

Máster en Machine Learning e Inteligencia Artificial
OBS Business School · Edición 2510 · Curso 2025–2026

**Empresa de referencia:** Seguros Pepín, S.A. (República Dominicana)

---

**Equipo de trabajo:**

- [Nombre y apellidos del integrante 1]
- [Nombre y apellidos del integrante 2]
- [Nombre y apellidos del integrante 3]
- [Nombre y apellidos del integrante 4]
- [Nombre y apellidos del integrante 5]
- [Nombre y apellidos del integrante 6]

**Tutor:** [Nombre del tutor]

**Fecha de entrega:** 26 de junio de 2026

---

## Declaración de autoría

Los integrantes del equipo declaran que el presente trabajo es original y de su autoría,
que se han citado adecuadamente todas las fuentes utilizadas conforme a la normativa APA
7.ª edición (Art. 7 de la normativa OBS), y que no incurre en plagio ni en uso indebido de
materiales de terceros.

Firmas:

| Integrante | Firma | Fecha |
|---|---|---|
| [Integrante 1] | | |
| [Integrante 2] | | |
| [Integrante 3] | | |
| [Integrante 4] | | |
| [Integrante 5] | | |
| [Integrante 6] | | |

---

## Índice de contenidos

1. **Arquitectura del sistema** — patrón Supervisor (Hub-and-Spoke), los seis agentes,
   flujo del expediente, gestión de estado, datos y conocimiento, capacidades de IA reales
   frente a integraciones simuladas, HITL y despliegue.
2. **Herramientas y capacidades** — herramientas `@tool` (mocks de sistemas externos) y
   capacidades de IA reales (extracción multimodal con Claude Vision, RAG de pólizas con
   ChromaDB, motor antifraude de cuatro detectores).
3. **Manual de usuario** — puesta en marcha (Docker, app Streamlit, CLI y API REST),
   operación, interpretación de resultados y resolución de problemas.
4. **Evaluación y resultados** — dataset sintético, protocolo, precisión, matriz de
   confusión, validación del motor antifraude y de la extracción multimodal.

---

\newpage
