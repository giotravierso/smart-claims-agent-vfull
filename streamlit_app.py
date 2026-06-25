"""
Smart-Claims Agent — Dashboard (despliegue Streamlit Cloud).

App AUTONOMA: invoca el grafo de agentes (`process_claim`) en el mismo
proceso, sin necesidad del backend FastAPI ni de MariaDB. Pensada para
desplegarse en Streamlit Community Cloud (un solo proceso Python).

Estetica: Salesforce Lightning + identidad de marca Seguros Pepin. Incluye
una pantalla de bienvenida (menu) con navegacion lateral.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid

import pandas as pd
import streamlit as st

# ── Acceso al paquete backend (app.*) ─────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "backend"))

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = str(st.secrets["ANTHROPIC_API_KEY"])
    if "HITL_AMOUNT_THRESHOLD" in st.secrets:
        os.environ["HITL_AMOUNT_THRESHOLD"] = str(st.secrets["HITL_AMOUNT_THRESHOLD"])
except Exception:
    pass

try:
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv())
except Exception:
    pass

from app.agents.orchestrator import process_claim  # noqa: E402


# ── Constantes de presentacion ────────────────────────────────────────────

LOGO_URL = "https://segurospepin.com/wp-content/uploads/2020/03/Layer-1-251x95.png"

C_PRIMARY      = "#0B4DA2"
C_PRIMARY_DARK = "#07336B"
C_ACCENT       = "#F39200"
C_BG           = "#F3F3F3"
C_CARD         = "#FFFFFF"
C_BORDER       = "#DDDBDA"
C_TEXT         = "#16325C"
C_TEXT_SOFT    = "#5C6B82"

AGENT_LABELS = {
    "agent_a_orchestrator":         "Agente A · Orquestador",
    "agent_b_document_validator":   "Agente B · Validación documental",
    "agent_c_multimodal_extractor": "Agente C · Extracción multimodal",
    "agent_d_coverage_checker":     "Agente D · Verificación de cobertura",
    "agent_e_claim_resolver":       "Agente E · Resolución",
    "agent_g_fraud_compliance":     "Agente G · Fraude y cumplimiento",
}

CLAIM_TYPES = {
    "danys_propis":    "Daños propios",
    "responsabilitat": "Responsabilidad civil",
    "robatori":        "Robo",
    "danys_mecanics":  "Daños mecánicos",
}

REQUIRED_DOCS_BY_TYPE = {
    "danys_propis":    ["foto_danys", "factura", "denuncia_companyia"],
    "responsabilitat": ["foto_danys", "acta_policial", "dades_tercer"],
    "robatori":        ["acta_policial", "llista_objectes_robats"],
    "danys_mecanics":  ["informe_taller", "factura"],
}

DECISION_STYLE = {
    "PAGO":            ("Resuelto · Pago aprobado", "success"),
    "RECHAZO":         ("Rechazado · Sin cobertura", "error"),
    "RECHAZO_FRAUDE":  ("Bloqueado · Fraude / OFAC", "error"),
    "REVISION_HUMANA": ("Revisión humana requerida", "warning"),
    "INFO_REQUERIDA":  ("Información requerida", "info"),
}

# Escenarios de demostración (uno por camino del flujo)
DEMO_SCENARIOS = [
    {"label": "Pago automático", "claim_type": "danys_propis", "amount": 2500.0,
     "docs": ["foto_danys", "factura", "denuncia_companyia"],
     "desc": "Daños propios · 2.500 € · documentación completa → PAGO"},
    {"label": "Revisión humana (HITL)", "claim_type": "responsabilitat", "amount": 9500.0,
     "docs": ["foto_danys", "acta_policial", "dades_tercer"],
     "desc": "Responsabilidad civil · 9.500 € → REVISIÓN HUMANA por importe"},
    {"label": "Información requerida", "claim_type": "danys_propis", "amount": 3000.0,
     "docs": ["factura"],
     "desc": "Daños propios · faltan documentos → SOLICITUD DE INFO"},
    {"label": "Rechazo por no cobertura", "claim_type": "danys_mecanics", "amount": 1500.0,
     "docs": ["informe_taller", "factura"],
     "desc": "Daños mecánicos · sin cobertura en póliza → RECHAZO"},
]


# ── Configuracion de pagina ───────────────────────────────────────────────

st.set_page_config(
    page_title="Smart-Claims Agent · Seguros Pepín",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── CSS — estetica Salesforce Lightning ───────────────────────────────────

st.markdown(f"""
<style>
    #MainMenu, footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ display: none; }}
    .stApp {{ background: {C_BG}; }}
    html, body, [class*="css"] {{
        font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .block-container {{ padding-top: 2.2rem; max-width: 1180px; }}

    .pill {{ display:inline-block; padding:4px 12px; border-radius:999px;
        font-size:12px; font-weight:600; }}
    .pill.success {{ background:#EAF5EC; color:#2E844A; border:1px solid #9BD0A8; }}
    .pill.error   {{ background:#FCE9E9; color:#BA0517; border:1px solid #F0A9A4; }}
    .pill.warning {{ background:#FEF3E6; color:#A35C00; border:1px solid #FAC685; }}
    .pill.info    {{ background:#EAF1FB; color:{C_PRIMARY}; border:1px solid #A9C4EC; }}
    .pill.neutral {{ background:#F1F1F1; color:#5C6B82; border:1px solid #DDDBDA; }}

    .sca-card {{ background:{C_CARD}; border:1px solid {C_BORDER}; border-radius:10px;
        padding:16px 18px; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
    .sca-metric .lbl {{ font-size:11px; text-transform:uppercase; letter-spacing:.6px;
        color:{C_TEXT_SOFT}; font-weight:600; }}
    .sca-metric .val {{ font-size:24px; font-weight:600; color:{C_TEXT}; margin-top:4px; }}
    .sca-metric .delta {{ font-size:11px; color:{C_TEXT_SOFT}; }}

    .sca-section {{ font-size:13px; font-weight:700; text-transform:uppercase;
        letter-spacing:.7px; color:{C_TEXT_SOFT}; margin:20px 0 10px 0; }}

    /* Botones primarios */
    .stButton > button, .stFormSubmitButton > button {{
        background:{C_PRIMARY}; color:#fff; border:none; border-radius:6px; font-weight:600; }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{ background:{C_PRIMARY_DARK}; color:#fff; }}

    section[data-testid="stSidebar"] {{ background:#FFFFFF; border-right:1px solid {C_BORDER}; }}
    section[data-testid="stSidebar"] .stButton > button {{
        background:transparent; color:{C_TEXT}; text-align:left; border:1px solid transparent;
        border-radius:6px; font-weight:600; }}
    section[data-testid="stSidebar"] .stButton > button:hover {{
        background:#EAF1FB; color:{C_PRIMARY}; border-color:#A9C4EC; }}
</style>
""", unsafe_allow_html=True)


# ── Cabecera (estilos en linea: robusta ante temas/bloqueos) ──────────────

st.markdown(f"""
<div style="background:linear-gradient(90deg,{C_PRIMARY_DARK} 0%,{C_PRIMARY} 100%);
     border-radius:10px;padding:16px 22px;margin:4px 0 18px 0;display:flex;
     align-items:center;gap:14px;box-shadow:0 2px 6px rgba(0,0,0,.12)">
  <span style="background:#fff;color:{C_PRIMARY};font-weight:800;font-size:12px;
        padding:6px 11px;border-radius:6px;letter-spacing:.6px;white-space:nowrap">SEGUROS PEPÍN</span>
  <span style="color:#fff;font-size:22px;font-weight:700;letter-spacing:.2px;
        white-space:nowrap">Smart-Claims Agent</span>
  <span style="color:#cfe0f5;font-size:12px;margin-left:auto;text-align:right;line-height:1.35">
     Gestión agéntica de siniestros<br/>Seguros Pepín, S.A.</span>
</div>
""", unsafe_allow_html=True)


# ── Estado / navegacion ────────────────────────────────────────────────────

if "view" not in st.session_state:
    st.session_state["view"] = "home"
if "history" not in st.session_state:
    st.session_state["history"] = []
if "prefill" not in st.session_state:
    st.session_state["prefill"] = None


def go(view: str, prefill=None) -> None:
    st.session_state["view"] = view
    if prefill is not None:
        st.session_state["prefill"] = prefill


# ── Utilidades de render ───────────────────────────────────────────────────

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def pill(label: str, kind: str) -> str:
    return f'<span class="pill {kind}">{label}</span>'


def decision_pill(result: dict) -> str:
    dec = result.get("decision")
    label, kind = DECISION_STYLE.get(dec, (result.get("status", "—"), "neutral"))
    return pill(label, kind)


def metric_card(lbl: str, val: str, delta: str = "") -> str:
    d = f'<div class="delta">{delta}</div>' if delta else ""
    return (f'<div class="sca-card sca-metric"><div class="lbl">{lbl}</div>'
            f'<div class="val">{val}</div>{d}</div>')


def _step_header(agent: str, action: str = "", flagged: bool = False) -> str:
    color = C_ACCENT if flagged else C_PRIMARY
    act = f'<span style="font-size:11px;color:{C_TEXT_SOFT}"> · {action}</span>' if action else ""
    return (f'<span style="font-size:12px;font-weight:700;color:{color};'
            f'text-transform:uppercase;letter-spacing:.4px">{agent}</span>{act}')


def render_timeline(result: dict) -> None:
    decisions = result.get("decisions_log") or []
    if decisions:
        for d in decisions:
            agent = AGENT_LABELS.get(d.get("agent", ""), d.get("agent", "Agente"))
            with st.container(border=True):
                st.markdown(_step_header(agent, d.get("action", ""), bool(d.get("hitl_required"))),
                            unsafe_allow_html=True)
                st.markdown(d.get("reasoning", "") or "_(sin razonamiento)_")
    else:
        for i, step in enumerate(result.get("reasoning_trace", []), 1):
            with st.container(border=True):
                st.markdown(_step_header(f"Paso {i}"), unsafe_allow_html=True)
                st.markdown(step)


def process_and_store(client_id, client_email, claim_type, amount, documents):
    claim_id = f"CLM-{uuid.uuid4().hex[:8].upper()}"
    with st.spinner("Procesando la reclamación con los agentes..."):
        start = time.time()
        result = _run(process_claim(
            claim_id=claim_id, client_id=client_id, claim_type=claim_type,
            amount_requested=float(amount), channel="web",
            documents=documents, client_email=client_email,
        ))
    result.update({"_elapsed": time.time() - start, "_claim_id": claim_id,
                   "_client_id": client_id, "_claim_type": claim_type,
                   "_amount_requested": float(amount)})
    st.session_state["last_result"] = result
    st.session_state["history"].insert(0, result)


def render_result(result: dict) -> None:
    amount_paid = (result.get("resolution") or {}).get("amount_paid")
    st.markdown(f"### Expediente {result.get('_claim_id', '')}")
    st.markdown(decision_pill(result), unsafe_allow_html=True)
    reason_term = result.get("termination_reason")
    if reason_term:
        st.caption(reason_term)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Estado", result.get("status", "—")), unsafe_allow_html=True)
    c2.markdown(metric_card("Decisión", result.get("decision") or "—"), unsafe_allow_html=True)
    c3.markdown(metric_card("Importe pagado",
                f"{amount_paid:,.0f} €" if amount_paid else "—",
                f"de {result.get('_amount_requested', 0):,.0f} € solicitados"),
                unsafe_allow_html=True)
    c4.markdown(metric_card("Tiempo", f"{result.get('_elapsed', 0):.1f} s"), unsafe_allow_html=True)

    fraud = result.get("fraud_result") or {}
    if fraud:
        verdict = fraud.get("verdict") or ("FLAGGED" if fraud.get("is_flagged") else "CLEAR")
        score = fraud.get("risk_score") or fraud.get("score")
        kind = "error" if fraud.get("is_flagged") else "success"
        extra = f" · score {score:.2f}" if isinstance(score, (int, float)) else ""
        st.markdown('<div class="sca-section">Cribado antifraude (Agente G)</div>', unsafe_allow_html=True)
        st.markdown(pill(f"{verdict}{extra}", kind), unsafe_allow_html=True)

    st.markdown('<div class="sca-section">Cadena de razonamiento de los agentes</div>', unsafe_allow_html=True)
    render_timeline(result)


# ── Navegacion lateral ─────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f'<div style="font-weight:700;color:{C_TEXT};font-size:13px;'
                f'text-transform:uppercase;letter-spacing:.6px;margin:4px 0 10px">Navegación</div>',
                unsafe_allow_html=True)
    st.button("Inicio",              key="nav_home",  use_container_width=True, on_click=go, args=("home",))
    st.button("Nueva reclamación",   key="nav_nueva", use_container_width=True, on_click=go, args=("nueva",))
    st.button("Historial",           key="nav_hist",  use_container_width=True, on_click=go, args=("historial",))
    st.button("Arquitectura",        key="nav_arq",   use_container_width=True, on_click=go, args=("arquitectura",))
    st.divider()
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    st.caption(("🟢 Claude activo (CoT enriquecido)" if has_key
                else "⚪ Modo fallback determinista (sin clave)"))


view = st.session_state["view"]


# ── Vista: HOME (bienvenida / menu) ────────────────────────────────────────

if view == "home":
    st.markdown("## Centro de Gestión de Siniestros")
    st.markdown("Bienvenido. Selecciona la acción que quieres realizar.")
    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("#### 📝 Nueva reclamación")
            st.write("Registra un expediente y procésalo con los seis agentes. "
                     "Verás la decisión final y el razonamiento (Chain of Thought).")
            st.button("Empezar", key="tile_nueva", use_container_width=True,
                      on_click=go, args=("nueva",))
    with col2:
        with st.container(border=True):
            st.markdown("#### 📋 Historial")
            st.write("Consulta los expedientes procesados en esta sesión, con su estado, "
                     "decisión y distribución.")
            st.button("Ver historial", key="tile_hist", use_container_width=True,
                      on_click=go, args=("historial",))

    col3, col4 = st.columns(2)
    with col3:
        with st.container(border=True):
            st.markdown("#### ⚡ Escenarios de demostración")
            st.write("Lanza con un clic los cuatro casos representativos del flujo "
                     "(pago, revisión humana, información, rechazo).")
            st.button("Ir a escenarios", key="tile_demo", use_container_width=True,
                      on_click=go, args=("nueva",))
    with col4:
        with st.container(border=True):
            st.markdown("#### 🏛 Arquitectura del sistema")
            st.write("Conoce el patrón Supervisor (Hub-and-Spoke), los seis agentes "
                     "y el motor antifraude de cuatro detectores.")
            st.button("Ver arquitectura", key="tile_arq", use_container_width=True,
                      on_click=go, args=("arquitectura",))


# ── Vista: NUEVA RECLAMACION ───────────────────────────────────────────────

elif view == "nueva":
    st.markdown("## Nueva reclamación")

    st.markdown('<div class="sca-section">Escenarios rápidos</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, sc in enumerate(DEMO_SCENARIOS):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"**{sc['label']}**")
                st.caption(sc["desc"])
                if st.button("Procesar", key=f"sc_{i}", use_container_width=True):
                    process_and_store("CLIENT-DEMO", "cliente@segurospepin.com",
                                      sc["claim_type"], sc["amount"], sc["docs"])

    st.markdown('<div class="sca-section">O crea una reclamación personalizada</div>',
                unsafe_allow_html=True)
    with st.form("claim_form"):
        a, b = st.columns(2)
        client_id = a.text_input("ID Cliente", value="CLIENT-A")
        client_email = b.text_input("Email del cliente", value="cliente@segurospepin.com")
        claim_type = a.selectbox("Tipo de siniestro", options=list(CLAIM_TYPES.keys()),
                                 format_func=lambda k: CLAIM_TYPES[k])
        amount = b.number_input("Importe reclamado (€)", min_value=0.0, max_value=100000.0,
                                value=2500.0, step=100.0)
        docs_avail = REQUIRED_DOCS_BY_TYPE.get(claim_type, [])
        documents = st.multiselect("Documentos aportados", options=docs_avail, default=docs_avail,
                                   help="Deselecciona alguno para simular documentación incompleta.")
        submitted = st.form_submit_button("Procesar reclamación", use_container_width=True)
    if submitted:
        process_and_store(client_id, client_email, claim_type, amount, documents)

    if st.session_state.get("last_result"):
        st.divider()
        render_result(st.session_state["last_result"])


# ── Vista: HISTORIAL ───────────────────────────────────────────────────────

elif view == "historial":
    st.markdown("## Historial de reclamaciones")
    history = st.session_state.get("history", [])
    if not history:
        st.info("Aún no se ha procesado ninguna reclamación en esta sesión.")
        st.button("Crear la primera", on_click=go, args=("nueva",))
    else:
        rows = [{
            "Expediente": r.get("_claim_id"), "Cliente": r.get("_client_id"),
            "Tipo": CLAIM_TYPES.get(r.get("_claim_type"), r.get("_claim_type")),
            "Estado": r.get("status"), "Decisión": r.get("decision"),
            "Solicitado (€)": r.get("_amount_requested"),
            "Pagado (€)": (r.get("resolution") or {}).get("amount_paid"),
        } for r in history]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown('<div class="sca-section">Distribución por decisión</div>', unsafe_allow_html=True)
        st.bar_chart(df["Decisión"].value_counts())


# ── Vista: ARQUITECTURA ────────────────────────────────────────────────────

elif view == "arquitectura":
    st.markdown("## Arquitectura del sistema")
    st.markdown("""
**Patrón Supervisor (Hub-and-Spoke) sobre LangGraph.** El Agente A (orquestador) es el único
que decide el flujo: lee el estado del expediente y enruta al siguiente agente especializado.
Cada agente hace su trabajo y devuelve el control al supervisor.
""")
    st.markdown('<div class="sca-section">Los seis agentes</div>', unsafe_allow_html=True)
    agents = [
        ("Agente A · Orquestador", "Supervisor central: triaje y enrutamiento del expediente."),
        ("Agente G · Fraude y cumplimiento", "Filtro de entrada: motor antifraude con 4 detectores "
         "(OFAC fuzzy, importe anómalo por Z-score, duplicados, coherencia documental) y veredicto graduado."),
        ("Agente B · Validación documental", "Comprueba la documentación requerida del expediente."),
        ("Agente C · Extracción multimodal", "Extrae datos de facturas/fotos/actas (VLM)."),
        ("Agente D · Verificación de cobertura", "Determina cobertura, límites y franquicia (RAG)."),
        ("Agente E · Resolución", "Decisión final: pago automático, rechazo o derivación a revisión humana."),
    ]
    for name, desc in agents:
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(desc)
    st.markdown('<div class="sca-section">Características clave</div>', unsafe_allow_html=True)
    st.markdown("""
- **Human-in-the-Loop (HITL):** revisión humana si hay fraude o si el importe supera el umbral (5.000 €).
- **Razonamiento (CoT) por agente**, con LLM Claude Sonnet 4.6 **opcional** y *fallback* determinista.
- **Persistencia auditable** de decisiones en MariaDB (en este despliegue, best-effort).
- **Integraciones externas simuladas** (mock): OFAC, pagos, notificaciones y RAG de pólizas.
""")
    st.button("← Volver al inicio", on_click=go, args=("home",))
