"""
Smart-Claims Agent — Dashboard Streamlit.

Interfaz de demostracion del sistema agentico. Permite enviar
reclamaciones de prueba y visualizar en tiempo real el Chain of Thought
completo de los agentes que las procesan.
"""
from __future__ import annotations

import os
import time

import httpx
import pandas as pd
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
API_BASE    = f"{BACKEND_URL}/api/v1/claims"


AGENT_LABELS = {
    "agent_a_orchestrator":         "Agente A — Orchestrator",
    "agent_b_document_validator":   "Agente B — Document Validator",
    "agent_c_multimodal_extractor": "Agente C — Multimodal Extractor",
    "agent_d_coverage_checker":     "Agente D — Coverage Checker",
    "agent_e_claim_resolver":       "Agente E — Claim Resolver",
    "agent_g_fraud_compliance":     "Agente G — Fraud Compliance",
}


CLAIM_TYPES = {
    "danys_propis":    "Danos propios",
    "responsabilitat": "Responsabilidad civil",
    "robatori":        "Robo",
    "danys_mecanics":  "Danos mecanicos",
    "default":         "Default",
}


REQUIRED_DOCS_BY_TYPE = {
    "danys_propis":    ["foto_danys", "factura", "denuncia_companyia"],
    "responsabilitat": ["foto_danys", "acta_policial", "dades_tercer"],
    "robatori":        ["acta_policial", "llista_objectes_robats"],
    "danys_mecanics":  ["informe_taller", "factura"],
    "default":         ["foto_danys", "factura"],
}


# ── Configuracion de pagina ───────────────────────────────────────────────

st.set_page_config(
    page_title            = "Smart-Claims Agent",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)


st.markdown("""
<style>
    .stApp { background-color: #FAFAF7; }
    h1, h2, h3 { color: #1A1A1A; font-weight: 500; }

    .decision-card {
        padding: 16px 20px;
        border-radius: 8px;
        margin: 8px 0;
        background: #FFFFFF;
        border: 1px solid #E5E5E0;
    }
    .decision-card h4 {
        margin: 0 0 8px 0;
        font-size: 13px;
        color: #5F5E5A;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .decision-card .reasoning {
        font-size: 14px;
        color: #1A1A1A;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    .decision-card .meta {
        font-size: 11px;
        color: #9A9A95;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ── Funciones API ─────────────────────────────────────────────────────────

def api_create_claim(payload: dict) -> dict:
    with httpx.Client(timeout=180.0) as client:
        response = client.post(f"{API_BASE}/", json=payload)
        response.raise_for_status()
        return response.json()


def api_get_trace(claim_id: str) -> dict:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE}/{claim_id}/trace")
        response.raise_for_status()
        return response.json()


def api_list_claims() -> list[dict]:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE}/")
        response.raise_for_status()
        return response.json()


# ── Helpers ───────────────────────────────────────────────────────────────

def render_decision_card(decision: dict) -> None:
    agent_label = AGENT_LABELS.get(decision["agent"], decision["agent"])
    action      = decision["action"]
    reasoning   = decision["reasoning"]
    created_at  = decision.get("created_at", "")

    st.markdown(f"""
    <div class="decision-card">
        <h4>{agent_label} &middot; {action}</h4>
        <div class="reasoning">{reasoning}</div>
        <div class="meta">{created_at} &middot; ID #{decision["id"]}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar — formulario de envio ─────────────────────────────────────────

st.sidebar.title("Nueva reclamacion")
st.sidebar.caption("Envia un caso de prueba al sistema agentico")

with st.sidebar.form("claim_form"):
    client_id    = st.text_input("ID Cliente", value="CLIENT-A")
    client_email = st.text_input("Email cliente", value="cliente@example.com")

    claim_type_key = st.selectbox(
        "Tipo de siniestro",
        options     = list(CLAIM_TYPES.keys()),
        format_func = lambda k: CLAIM_TYPES[k],
    )

    amount = st.number_input(
        "Importe reclamado (EUR)",
        min_value = 0.0,
        max_value = 100000.0,
        value     = 2500.0,
        step      = 100.0,
    )

    available_docs = REQUIRED_DOCS_BY_TYPE.get(claim_type_key, [])
    documents = st.multiselect(
        "Documentos aportados",
        options = available_docs,
        default = available_docs,
        help    = "Deselecciona alguno para simular documentacion incompleta",
    )

    text = st.text_area(
        "Texto de la reclamacion",
        value  = "Reclamacion por danos en mi vehiculo tras un accidente.",
        height = 100,
    )

    submitted = st.form_submit_button("Procesar reclamacion", use_container_width=True)


# ── Cuerpo principal ──────────────────────────────────────────────────────

st.title("Smart-Claims Agent")
st.caption("Sistema agentico para la gestion de reclamaciones — TFM OBS Business School")

tab_demo, tab_history = st.tabs(["Demostracion en vivo", "Historial"])


# ── Tab 1 — Demostracion en vivo ──────────────────────────────────────────

with tab_demo:

    if submitted:
        payload = {
            "client_id":        client_id,
            "client_email":     client_email,
            "claim_type":       claim_type_key,
            "amount_requested": amount,
            "documents":        documents,
            "text":             text,
        }

        with st.spinner("Procesando reclamacion (puede tardar entre 20 y 60 segundos)..."):
            start = time.time()
            try:
                result  = api_create_claim(payload)
                elapsed = time.time() - start
                st.session_state["last_claim_id"]      = result["claim_id"]
                st.session_state["last_claim_result"]  = result
                st.session_state["last_claim_elapsed"] = elapsed
            except httpx.HTTPStatusError as e:
                st.error(f"Error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                st.error(f"Error procesando la reclamacion: {e}")

    if "last_claim_result" in st.session_state:
        result   = st.session_state["last_claim_result"]
        elapsed  = st.session_state.get("last_claim_elapsed", 0)
        claim_id = result["claim_id"]

        st.subheader(f"Expediente {claim_id}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Estado",     result["status"])
        col2.metric("Decision",   result.get("decision") or "—")
        col3.metric(
            "Importe pagado",
            f"{result.get('amount_paid') or 0:.2f} EUR",
            delta = f"de {result.get('amount_requested') or 0:.2f} EUR solicitados",
        )
        col4.metric("Tiempo proceso", f"{elapsed:.1f} s")

        if result.get("hitl_required"):
            st.warning(
                f"Revision humana requerida — {result.get('termination_reason', 'importe sobre umbral')}"
            )
        elif result["status"] == "resolved":
            st.success(f"Reclamacion resuelta automaticamente — {result.get('termination_reason')}")
        elif result["status"] == "rejected":
            st.error(f"Reclamacion rechazada — {result.get('termination_reason')}")
        elif result["status"] == "validating":
            st.info("Documentacion incompleta — cliente notificado")

        st.subheader("Chain of Thought de los agentes")
        st.caption("Cada tarjeta muestra el razonamiento de un agente del sistema")

        try:
            trace     = api_get_trace(claim_id)
            decisions = trace.get("decisions", [])

            if not decisions:
                st.info("Sin decisiones registradas para este expediente.")
            else:
                for decision in decisions:
                    render_decision_card(decision)

        except Exception as e:
            st.error(f"No se pudo cargar la traza: {e}")

    else:
        st.info("Configura la reclamacion en el panel lateral y pulsa 'Procesar reclamacion'.")

        with st.expander("Escenarios de prueba sugeridos"):
            st.markdown("""
**Escenario 1 — Pago automatico**
Tipo: Danos propios &middot; Importe: 2500 EUR &middot; Todos los documentos aportados.
Resultado esperado: pago automatico tras franquicia.

**Escenario 2 — Revision humana (HITL)**
Tipo: Responsabilidad &middot; Importe: 9500 EUR &middot; Todos los documentos aportados.
Resultado esperado: HITL activado por superar el umbral de 5000 EUR.

**Escenario 3 — Documentacion incompleta**
Tipo: Danos propios &middot; Importe: 3000 EUR &middot; Solo foto_danys.
Resultado esperado: solicitud de documentacion adicional al cliente.

**Escenario 4 — No cobertura**
Tipo: Danos mecanicos &middot; Importe: 1500 EUR &middot; Documentos completos.
Resultado esperado: rechazo justificado.
            """)


# ── Tab 2 — Historial ─────────────────────────────────────────────────────

with tab_history:
    st.subheader("Historial de reclamaciones procesadas")

    try:
        claims = api_list_claims()
    except Exception as e:
        st.error(f"No se pudo cargar el historial: {e}")
        claims = []

    if not claims:
        st.info("Aun no se ha procesado ninguna reclamacion.")
    else:
        df = pd.DataFrame(claims)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
            df = df.sort_values("created_at", ascending=False)

        df_display = df[[
            c for c in [
                "id", "client_id", "claim_type", "status",
                "amount_requested", "amount_approved", "created_at",
            ] if c in df.columns
        ]].rename(columns={
            "id":               "Expediente",
            "client_id":        "Cliente",
            "claim_type":       "Tipo",
            "status":           "Estado",
            "amount_requested": "Importe solicitado",
            "amount_approved":  "Importe aprobado",
            "created_at":       "Creado",
        })

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.subheader("Distribucion por estado")
        if "status" in df.columns:
            status_counts = df["status"].value_counts()
            st.bar_chart(status_counts)

        selected = st.selectbox(
            "Ver traza CoT de un expediente",
            options = [""] + df["id"].tolist() if "id" in df.columns else [""],
        )

        if selected:
            try:
                trace = api_get_trace(selected)
                for d in trace.get("decisions", []):
                    render_decision_card(d)
            except Exception as e:
                st.error(f"No se pudo cargar la traza de {selected}: {e}")
