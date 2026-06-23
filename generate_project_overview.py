"""
Genera el PDF de descripción del proyecto Smart-Claims Agent.
Uso: python3 generate_project_overview.py
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import date

OUTPUT = "Smart-Claims_Agent_Descripcion_Proyecto.pdf"

# ── Colores corporativos ──────────────────────────────────────────────────────
DARK_BLUE  = colors.HexColor("#1A3A5C")
MID_BLUE   = colors.HexColor("#2E6DA4")
LIGHT_BLUE = colors.HexColor("#D6E8F7")
ACCENT     = colors.HexColor("#E8A020")
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY   = colors.HexColor("#AAAAAA")
TEXT_DARK  = colors.HexColor("#1C1C1C")


def build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontSize=22, textColor=DARK_BLUE,
            spaceAfter=4, spaceBefore=0,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=11, textColor=MID_BLUE,
            spaceAfter=2, alignment=TA_CENTER,
            fontName="Helvetica",
        ),
        "meta": ParagraphStyle(
            "meta", parent=base["Normal"],
            fontSize=9, textColor=MID_GRAY,
            spaceAfter=0, alignment=TA_CENTER,
            fontName="Helvetica-Oblique",
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"],
            fontSize=13, textColor=colors.white,
            spaceAfter=0, spaceBefore=0,
            fontName="Helvetica-Bold",
            leftIndent=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=11, textColor=DARK_BLUE,
            spaceAfter=4, spaceBefore=10,
            fontName="Helvetica-Bold",
            borderPad=2,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9.5, textColor=TEXT_DARK,
            spaceAfter=4, spaceBefore=2,
            fontName="Helvetica",
            leading=14,
        ),
        "code": ParagraphStyle(
            "code", parent=base["Code"],
            fontSize=8.5, textColor=DARK_BLUE,
            fontName="Courier",
            leftIndent=12, spaceAfter=2,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=base["Normal"],
            fontSize=9.5, textColor=TEXT_DARK,
            spaceAfter=3, leftIndent=14, firstLineIndent=-10,
            fontName="Helvetica", leading=13,
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"],
            fontSize=9, textColor=colors.white,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"],
            fontSize=8.5, textColor=TEXT_DARK,
            fontName="Helvetica", leading=12,
        ),
        "table_cell_mono": ParagraphStyle(
            "table_cell_mono", parent=base["Normal"],
            fontSize=8, textColor=DARK_BLUE,
            fontName="Courier", leading=11,
        ),
        "caption": ParagraphStyle(
            "caption", parent=base["Normal"],
            fontSize=8, textColor=MID_GRAY,
            fontName="Helvetica-Oblique", alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=8, textColor=MID_GRAY,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }
    return styles


def section_header(title, styles):
    """Cabecera de sección con fondo azul oscuro."""
    data = [[Paragraph(title, styles["h1"])]]
    t = Table(data, colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t


def file_table(rows, styles, col_widths=None):
    """Tabla de archivos con cabecera azul y filas alternadas."""
    if col_widths is None:
        col_widths = [6 * cm, 11 * cm]

    header = [
        Paragraph("Archivo", styles["table_header"]),
        Paragraph("Descripción", styles["table_header"]),
    ]
    table_data = [header]
    for fname, desc in rows:
        table_data.append([
            Paragraph(fname, styles["table_cell_mono"]),
            Paragraph(desc, styles["table_cell"]),
        ])

    t = Table(table_data, colWidths=col_widths)
    style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  MID_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t


def arch_table(rows, styles):
    """Tabla de arquitectura (3 columnas)."""
    header = [
        Paragraph("Capa / Componente", styles["table_header"]),
        Paragraph("Tecnología", styles["table_header"]),
        Paragraph("Estado", styles["table_header"]),
    ]
    table_data = [header] + [
        [Paragraph(a, styles["table_cell"]),
         Paragraph(b, styles["table_cell"]),
         Paragraph(c, styles["table_cell"])]
        for a, b, c in rows
    ]
    t = Table(table_data, colWidths=[5.5 * cm, 7.5 * cm, 4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  MID_BLUE),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    styles = build_styles()
    story = []

    # ── PORTADA ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph("Smart-Claims Agent", styles["title"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Sistema Agéntico de Procesamiento Multimodal<br/>para la Gestión de Incidencias",
        styles["subtitle"]
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=6))
    story.append(Paragraph(
        f"OBS Business School · Máster en Machine Learning e IA · Edición 2510 · {date.today().strftime('%d/%m/%Y')}",
        styles["meta"]
    ))
    story.append(Spacer(1, 0.8 * cm))

    # ── 1. RESUMEN EJECUTIVO ───────────────────────────────────────────────
    story.append(section_header("1. Resumen ejecutivo", styles))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "MVP de agente IA autónomo que gestiona el ciclo completo de una reclamación de siniestro "
        "para <b>Seguros Pepín S.A.</b> (empresa real). El agente integra LLMs con capacidades "
        "de visión (VLM) y ejecución de herramientas (Function Calling) para analizar correos y "
        "documentos adjuntos, contrastarlos con pólizas corporativas y ejecutar automáticamente "
        "la resolución óptima (pago, rechazo o solicitud de información), reduciendo la intervención "
        "manual en back-office.",
        styles["body"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 2. ARQUITECTURA ────────────────────────────────────────────────────
    story.append(section_header("2. Arquitectura del sistema", styles))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "El sistema se organiza en <b>5 capas funcionales</b> más 2 transversales:",
        styles["body"]
    ))
    story.append(Spacer(1, 0.2 * cm))

    bullets_arch = [
        ("<b>Capa 1 — Canales de entrada:</b> Email, portal web, WhatsApp (simulado), API REST."),
        ("<b>Capa 2 — Orquestación (Agente A):</b> LangGraph + ReAct. Gestión de estado por expediente, "
         "router de agentes y Human-in-the-Loop (HITL)."),
        ("<b>Capa 3 — Agentes especializados:</b> Agente B (validación documental), C (extracción VLM), "
         "D (cobertura RAG), E (resolución autónoma), G (fraude/OFAC)."),
        ("<b>Capa 4 — Datos y conocimiento:</b> ChromaDB para RAG de pólizas · MariaDB para log de decisiones y HITL."),
        ("<b>Capa 5 — Integración simulada:</b> Mock APIs Python decoradas con @tool de LangChain."),
        ("<b>Transversal T1 — Seguridad:</b> Anonimización, control de acceso, auditoría."),
        ("<b>Transversal T2 — Observabilidad:</b> Trazas CoT visibles, métricas, dashboard Streamlit."),
    ]
    for b in bullets_arch:
        story.append(Paragraph(f"• {b}", styles["bullet"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Flujo de una reclamación:</b>", styles["body"]))
    flow_steps = [
        "Cliente envía reclamación  →  [A] Orquestador (triaje y enrutamiento)",
        "[G] Verificación OFAC/fraude  →  [B] Validación documental",
        "[C] Extracción VLM (fotos, facturas, actas)  →  [D] Verificación cobertura RAG",
        "[E] Decisión autónoma: PAGO (≤ umbral) · HITL revisión humana (> umbral) · RECHAZO justificado",
    ]
    for step in flow_steps:
        story.append(Paragraph(f"  {step}", styles["code"]))
    story.append(Spacer(1, 0.4 * cm))

    # ── 3. STACK TECNOLÓGICO ───────────────────────────────────────────────
    story.append(section_header("3. Stack tecnológico", styles))
    story.append(Spacer(1, 0.3 * cm))
    tech_rows = [
        ("LLM / VLM",           "Claude Sonnet (claude-sonnet-4-20250514)",    "✅ Decidido"),
        ("Framework agéntico",  "LangGraph + LangChain",                       "✅ Decidido"),
        ("RAG (pólizas)",       "ChromaDB 0.5.3 + LangChain",                  "✅ Decidido"),
        ("Backend",             "Python 3.11 + FastAPI + Uvicorn",             "✅ Operativo"),
        ("ORM / async DB",      "SQLAlchemy 2.0 + aiomysql",                   "✅ Operativo"),
        ("Base de datos",       "MariaDB 11.3",                                "✅ Operativo"),
        ("Frontend demo",       "Streamlit 1.36",                              "✅ Skeleton"),
        ("Contenerización",     "Docker + Compose (5 servicios)",              "✅ Operativo"),
        ("OCR (fallback)",      "Tesseract + pytesseract",                     "✅ Instalado"),
        ("llama-index",         "Excluido del build inicial (~2 GB)",          "🔄 Sprint 3"),
    ]
    story.append(arch_table(tech_rows, styles))
    story.append(Spacer(1, 0.4 * cm))

    # ── 4. DESCRIPCIÓN DE ARCHIVOS ─────────────────────────────────────────
    story.append(section_header("4. Descripción de archivos del proyecto", styles))
    story.append(Spacer(1, 0.3 * cm))

    # 4.1 Raíz
    story.append(Paragraph("4.1 Raíz del proyecto", styles["h2"]))
    root_rows = [
        ("CONTEXT_TFM.md",      "Documento maestro del TFM: arquitectura, cronograma, KPIs y estado actual. Knowledge document compartido con Claude."),
        ("README.md",           "Guía de inicio rápido del repositorio para el equipo."),
        ("docker-compose.yml",  "Orquesta los 5 contenedores Docker del proyecto (backend, frontend, ChromaDB, MariaDB, Adminer)."),
        ("setup.sh",            "Script bash de inicialización: crea .env, genera __init__.py, crea directorios data/ y arranca Docker Compose."),
        (".env / .env.example", "Variables de entorno (credenciales DB, ANTHROPIC_API_KEY, umbral HITL). El .env real está en .gitignore."),
        (".gitignore",          "Excluye del repositorio: .env, __pycache__, datos locales, etc."),
    ]
    story.append(KeepTogether(file_table(root_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.2 Backend — Entrypoint
    story.append(Paragraph("4.2 Backend — Entrypoint", styles["h2"]))
    backend_root_rows = [
        ("backend/app/main.py",        "Punto de entrada de FastAPI. Registra los 3 routers, configura CORS para Streamlit e inicializa la BD al arrancar."),
        ("backend/Dockerfile",         "Imagen Docker del backend (Python 3.11 + todas las dependencias)."),
        ("backend/requirements.txt",   "Dependencias Python: FastAPI, LangGraph, LangChain, Anthropic SDK, SQLAlchemy, ChromaDB, Pillow/Tesseract, aiomysql."),
    ]
    story.append(KeepTogether(file_table(backend_root_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.3 Agentes
    story.append(Paragraph("4.3 Agentes — backend/app/agents/", styles["h2"]))
    agents_rows = [
        ("orchestrator.py",
         "Agente A: orquestrador central. Implementa ReAct con LangGraph. Recibe una reclamación, "
         "la analiza con Claude Sonnet y enruta a agentes B/C/D/E/G según las herramientas que el "
         "LLM decide llamar. Incluye nodo HITL para casos >5.000€. Los agentes B-G son stubs pendientes."),
    ]
    story.append(KeepTogether(file_table(agents_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.4 Herramientas
    story.append(Paragraph("4.4 Herramientas (Mock APIs) — backend/app/tools/", styles["h2"]))
    tools_rows = [
        ("claim_tools.py",
         "Las 8 herramientas @tool que el LLM puede invocar: validate_documents, extract_multimodal, "
         "check_policy, approve_payment, send_rejection, request_more_info, check_fraud, log_decision. "
         "Todas son mocks que simulan sistemas externos reales; se sustituirán por integraciones reales en Fase II."),
    ]
    story.append(KeepTogether(file_table(tools_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.5 Base de datos
    story.append(Paragraph("4.5 Base de datos — backend/app/db/ y backend/db/", styles["h2"]))
    db_rows = [
        ("app/db/session.py",  "Configura la conexión async a MariaDB con SQLAlchemy + aiomysql. Lee credenciales desde variables de entorno."),
        ("app/db/models.py",   "Modelos ORM: Claim (expediente con estado y tipo de siniestro) y AgentDecision (log de decisiones con razonamiento CoT)."),
        ("db/init.sql",        "Script SQL de inicialización: crea tablas claims, agent_decisions, hitl_feedback e inserta 3 expedientes de demo (CLM-001/002/003)."),
    ]
    story.append(KeepTogether(file_table(db_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.6 Routers
    story.append(Paragraph("4.6 Routers — backend/app/routers/", styles["h2"]))
    routers_rows = [
        ("health.py",   "GET /health — devuelve {status: ok, version: 0.2.0}."),
        ("claims.py",   "POST /api/v1/claims/ y GET /api/v1/claims/{id}. Stubs; integración con orquestrador pendiente (Entrega 2)."),
        ("agents.py",   "GET /api/v1/agents/status — lista los 6 agentes indicando cuál está implementado (agent_a) y cuáles son stubs."),
    ]
    story.append(KeepTogether(file_table(routers_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.7 Frontend
    story.append(Paragraph("4.7 Frontend — frontend/", styles["h2"]))
    frontend_rows = [
        ("app.py",          "Skeleton Streamlit (una línea). El dashboard completo con CoT visible y panel HITL está pendiente de Entrega 2."),
        ("Dockerfile",      "Imagen Docker del frontend Streamlit."),
        ("requirements.txt","Dependencias del frontend (Streamlit y librerías auxiliares)."),
    ]
    story.append(KeepTogether(file_table(frontend_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.8 CI/CD
    story.append(Paragraph("4.8 CI/CD — .github/workflows/", styles["h2"]))
    cicd_rows = [
        ("dependency-audit.yml",
         "GitHub Action semanal (lunes) y en push a main. Ejecuta pip-audit y safety sobre los "
         "requirements.txt, sube reportes como artefactos y abre issues automáticos si encuentra "
         "vulnerabilidades críticas."),
    ]
    story.append(KeepTogether(file_table(cicd_rows, styles)))
    story.append(Spacer(1, 0.3 * cm))

    # 4.9 Scripts de auditoría
    story.append(Paragraph("4.9 Scripts de auditoría (raíz, no rastreados en git)", styles["h2"]))
    audit_rows = [
        ("dependency_audit.py",          "Audita dependencias Python en busca de CVEs conocidos."),
        ("comprehensive_security_audit.py","Auditoría de seguridad amplia del proyecto."),
        ("bundle_analysis.py",            "Analiza el tamaño del bundle de dependencias."),
        ("update_dependencies.py",        "Ayuda a actualizar dependencias de forma controlada."),
        ("*_report.md / *_README.md",     "Reportes y documentación generados por los scripts anteriores."),
    ]
    story.append(KeepTogether(file_table(audit_rows, styles)))
    story.append(Spacer(1, 0.4 * cm))

    # ── 5. SERVICIOS DOCKER ────────────────────────────────────────────────
    story.append(section_header("5. Servicios Docker", styles))
    story.append(Spacer(1, 0.3 * cm))
    docker_rows = [
        ("Backend FastAPI",  "sca-backend",   ":8000",  "✅ Operativo"),
        ("Frontend Streamlit","sca-frontend", ":8501",  "✅ Skeleton"),
        ("ChromaDB (RAG)",   "sca-chromadb",  ":8080",  "✅ Operativo"),
        ("MariaDB",          "sca-mariadb",   ":3306",  "✅ Operativo"),
        ("Adminer (DB UI)",  "sca-adminer",   ":8082",  "✅ Operativo"),
    ]
    header_d = [
        Paragraph("Servicio",   styles["table_header"]),
        Paragraph("Contenedor", styles["table_header"]),
        Paragraph("Puerto",     styles["table_header"]),
        Paragraph("Estado",     styles["table_header"]),
    ]
    docker_table_data = [header_d] + [
        [Paragraph(a, styles["table_cell"]), Paragraph(b, styles["table_cell_mono"]),
         Paragraph(c, styles["table_cell_mono"]), Paragraph(d, styles["table_cell"])]
        for a, b, c, d in docker_rows
    ]
    dt = Table(docker_table_data, colWidths=[5 * cm, 5 * cm, 3 * cm, 4 * cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  MID_BLUE),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ALIGN",         (2, 0), (2, -1), "CENTER"),
        ("ALIGN",         (3, 0), (3, -1), "CENTER"),
    ]))
    story.append(dt)
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "Arranque: <font name='Courier'>docker compose up -d</font> desde la raíz del repositorio.",
        styles["body"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── 6. ESTADO ACTUAL ──────────────────────────────────────────────────
    story.append(section_header("6. Estado actual y próximos pasos", styles))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Completado:</b>", styles["body"]))
    done = [
        "Infraestructura Docker operativa (5 servicios)",
        "Schema MariaDB: tablas claims, agent_decisions, hitl_feedback",
        "FastAPI operativo: /health, /api/v1/claims, /api/v1/agents/status",
        "Agente A — Orquestador LangGraph ReAct implementado",
        "Mock APIs completas (8 tools con @tool LangChain)",
        "Frontend Streamlit skeleton operativo",
        "Entrega 1 entregada (08/05/2026)",
    ]
    for item in done:
        story.append(Paragraph(f"✅ {item}", styles["bullet"]))

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("<b>En curso — Entrega 2 (hasta 26/06/2026):</b>", styles["body"]))
    pending = [
        "Dataset sintético de siniestros (data/synthetic/)",
        "Ingesta de pólizas en ChromaDB (scripts/ingest_policies.py)",
        "Agentes B, C, D, E, G — implementación completa",
        "Dashboard Streamlit completo (CoT visible, panel HITL)",
        "Capítulo de Arquitectura en la memoria escrita",
        "Fijar targets numéricos de los KPIs",
        "Vídeo de demostración (≤ 4 min)",
    ]
    for item in pending:
        story.append(Paragraph(f"⏳ {item}", styles["bullet"]))

    story.append(Spacer(1, 0.4 * cm))

    # ── PIE DE PÁGINA ──────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=MID_GRAY, spaceAfter=6))
    story.append(Paragraph(
        f"Smart-Claims Agent · OBS Business School · Máster ML &amp; IA · Edición 2510 · Generado el {date.today().strftime('%d/%m/%Y')}",
        styles["footer"]
    ))

    doc.build(story)
    print(f"PDF generado: {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
