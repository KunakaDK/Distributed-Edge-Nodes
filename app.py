import time
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timezone, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
API_URL  = "https://cloudserver-g09.southafricanorth.cloudapp.azure.com"
API_KEY  = "edge-secret-key-2026"
MICRO_B  = "http://10.70.22.189:8001"
HEADERS  = {"x-api-key": API_KEY}

st.set_page_config(
    page_title="EdgePulse · G09",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Thème (session state) ──────────────────────────────────────────────────────
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

dark = st.session_state.dark_mode

# ── Variables de thème ─────────────────────────────────────────────────────────
# Palette réduite : accent unique + vert (ok) + rouge (alerte), c'est tout.
if dark:
    T = dict(
        bg="#0A0E1A", bg2="#0F1525", bg3="#151C30", border="#1E2A45",
        text="#E8EDF5", muted="#64748B", subtext="#94A3B8",
        accent="#00D4FF", accent2="#00D4FF",          # un seul accent
        green="#00E5A0", orange="#00D4FF", red="#FF3B5C", yellow="#64748B",
        banner_bg="linear-gradient(135deg,#0F1525 0%,#151C30 50%,#0A1628 100%)",
        kpi_bg="linear-gradient(135deg,#0F1525 0%,#151C30 100%)",
        svc_bg="#0F1525",
        chart_grid="#1E2A45",
        chart_font="#64748B",
        chart_title="#E8EDF5",
        plot_bg="rgba(0,0,0,0)",
        stats_bg="#0F1525",
        divider="linear-gradient(90deg,transparent,#1E2A45,transparent)",
        footer_color="#1E2A45",
        toggle_icon="☀️", toggle_label="Mode clair",
        toggle_bg="#1E2A45", toggle_color="#94A3B8",
    )
else:
    T = dict(
        bg="#F1F5F9", bg2="#FFFFFF", bg3="#E2EAF4", border="#CBD5E1",
        text="#0F172A", muted="#475569", subtext="#334155",
        accent="#1D4ED8", accent2="#1D4ED8",          # un seul accent
        green="#059669", orange="#1D4ED8", red="#DC2626", yellow="#94A3B8",
        banner_bg="rgba(30, 58, 98, 0.9)",
        kpi_bg="linear-gradient(135deg,#FFFFFF 0%,#F8FAFC 100%)",
        svc_bg="#FFFFFF",
        chart_grid="#CBD5E1",
        chart_font="#475569",
        chart_title="#0F172A",
        plot_bg="rgba(255,255,255,0)",
        stats_bg="#EFF6FF",
        divider="linear-gradient(90deg,transparent,#CBD5E1,transparent)",
        footer_color="#94A3B8",
        toggle_icon="🌙", toggle_label="Mode sombre",
        toggle_bg="#DBEAFE", toggle_color="#1E40AF",
    )

# ── Chargement des images de fond en base64 ───────────────────────────────────
import base64, os

def load_bg_image(path):
    if os.path.exists(path):
        ext = path.rsplit(".", 1)[-1].lower()
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/{mime};base64,{data}"
    return None

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
bg_dark_path  = os.path.join(DASHBOARD_DIR, "bg_dark.png")
bg_light_path = os.path.join(DASHBOARD_DIR, "bg_light.png")

bg_image_b64 = load_bg_image(bg_dark_path if dark else bg_light_path)

overlay_color = "rgba(0,0,0,0)" if dark else "rgba(0,0,0,0)"
bg_solid      = "transparent"          if bg_image_b64 else T['bg']

if bg_image_b64:
    bg_css = (
        "body, div.stApp {"
        "  background-image: url('" + bg_image_b64 + "') !important;"
        "  background-size: cover !important;"
        "  background-attachment: fixed !important;"
        "  background-position: center center !important;"
        "  background-repeat: no-repeat !important;"
        "}"
        "div[data-testid='stAppViewContainer']::before {"
        "  content: '';"
        "  position: fixed;"
        "  inset: 0;"
        "  background: " + overlay_color + ";"
        "  z-index: 0;"
        "  pointer-events: none;"
        "}"
        "div[data-testid='stAppViewContainer'] > * {"
        "  position: relative;"
        "  z-index: 1;"
        "}"
    )
else:
    bg_css = ""

# ── Couleurs de graphiques unifiées (2 seulement : accent + rouge) ─────────────
C_EDGE  = T['accent']   # toutes les courbes Edge / données
C_CLOUD = T['muted']    # Cloud / secondaire
C_ALERT = T['red']      # seuils et alertes

# ── CSS dynamique ──────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

{bg_css}

/* ── Base ── */
html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
    background-color: {bg_solid} !important;
    color: {T['text']} !important;
}}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{
    padding: 1.5rem 2rem 2rem;
    max-width: 1400px;
    /* Compense la hauteur du banner fixe */
    padding-top: 5.5rem;
}}
div[data-testid="stDecoration"] {{ display: none; }}

/* ── Streamlit internal overrides ── */
section[data-testid="stSidebar"],
div[data-testid="stAppViewContainer"],
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
div[data-testid="column"],
div.stApp,
div.main {{
    background-color: {bg_solid} !important;
}}
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li,
div[data-testid="stMarkdownContainer"] strong,
label, span, p {{
    color: {T['text']} !important;
}}
/* Bouton toggle */
button[kind="secondary"], button[data-testid="baseButton-secondary"] {{
    background-color: {T['toggle_bg']} !important;
    color: {T['toggle_color']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 20px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: .7rem !important;
    letter-spacing: .05em !important;
}}
button[kind="secondary"]:hover {{
    background-color: {T['border']} !important;
}}
div[data-testid="stAlert"] {{
    background-color: {T['bg2']} !important;
    color: {T['text']} !important;
    border-color: {T['border']} !important;
}}
.stDataFrame, .stDataFrame th, .stDataFrame td {{
    background-color: {T['bg2']} !important;
    color: {T['text']} !important;
    border-color: {T['border']} !important;
}}
iframe[data-testid="stDataFrame"] {{ background-color: {T['bg2']} !important; }}
div[data-testid="stSpinner"] p {{ color: {T['muted']} !important; }}

/* ══════════════════════════════════════════════════════════════
   BANNER FIXE — HTML pur, indépendant de Streamlit
══════════════════════════════════════════════════════════════ */
#edgepulse-banner {{
    background: {T['banner_bg']};
    border-bottom: 1px solid {T['border']};
    border-top: 3px solid {T['accent']};
    padding: 0.8rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    position: fixed;
    top: 0; left: 0; right: 0;
    z-index: 99999;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
}}
.banner-title {{
    font-family: 'Space Mono', monospace;
    font-size: 1.05rem; font-weight: 700;
    color: {'#00D4FF' if dark else '#FFFFFF'};
    letter-spacing: -0.02em; line-height: 1.2;
}}
.banner-sub {{
    font-size: 0.66rem;
    color: {'rgba(100,116,139,1)' if dark else 'rgba(255,255,255,0.65)'};
    margin-top: 2px; letter-spacing: 0.06em; text-transform: uppercase;
}}
.banner-dot {{
    width: 8px; height: 8px; background: {T['green']}; border-radius: 50%;
    box-shadow: 0 0 10px {T['green']}; display: inline-block;
    margin-right: 7px; animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity:1; transform:scale(1); }}
    50%      {{ opacity:.5; transform:scale(.85); }}
}}
.banner-status {{
    font-family: 'Space Mono', monospace; font-size: 0.68rem;
}}

/* ── Section labels ── */
.section-label {{
    font-family: 'Space Mono', monospace; font-size: 0.62rem;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: {T['muted']}; margin-bottom: 0.75rem;
    border-left: 2px solid {T['accent']}; padding-left: 10px;
}}

/* ── KPI cards ── */
.kpi-card {{
    background: linear-gradient(130deg, rgba(10, 124, 179, 1) 0%, rgb(25, 117, 161, 1)  20%, #5673c5 60%, rgba(55, 84, 163, 0.8) 100%); border: 2px solid rgba(232, 229, 254, 1);
    box-shadow: 0 5px 5px rgba(30, 30, 30, 0.3), 
                0 0 0 1px rgb(232, 229, 254) inset;
    border-radius: 12px; padding: 1.2rem 1.4rem;
    position: relative; overflow: hidden; height: 100%;
}}
.kpi-value {{
    font-family: 'Space Mono', monospace; font-size: 1.8rem; font-weight: 700;
    color: {T['text']}; line-height: 1; margin-bottom: 2px;
}}
.kpi-unit  {{ font-family: 'Space Mono', monospace; font-size: .85rem; color: {T['muted']}; }}
.kpi-label {{ font-size: .72rem; color: {T['muted']}; text-transform: uppercase;
              letter-spacing: .08em; margin-top: 4px; }}

/* ── Latence cards — alignement vertical centré ── */
.lat-section {{
    display: flex;
    align-items: center;   /* toutes les colonnes même hauteur */
    gap: 1rem;
    border: 2px solid white;
}}
.lat-card {{
    background: linear-gradient(130deg, rgba(10, 124, 179, 1) 0%, rgb(25, 117, 161, 1)  20%, #5673c5 60%, rgba(55, 84, 163, 0.8) 100%); border: 2px solid rgba(232, 229, 254, 1);
    box-shadow: 0 5px 5px rgba(30, 30, 30, 0.3), 
                0 0 0 1px rgb(232, 229, 254) inset;
    border-radius: 16px; padding: 1.6rem; text-align: center;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
}}
.lat-badge {{
    font-family: 'Space Mono', monospace; font-size: .6rem; letter-spacing: .2em;
    text-transform: uppercase; padding: 3px 10px; border-radius: 20px;
    display: inline-block; margin-bottom: .9rem;
}}
.lat-badge-edge  {{ background: {T['accent']}18; color: {T['accent']}; border: 1px solid {T['accent']}44; }}
.lat-badge-cloud {{ background: {T['muted']}18; color: {T['muted']};  border: 1px solid {T['muted']}44; }}
.lat-value {{ font-family: 'Space Mono', monospace; font-size: 2.8rem; font-weight: 700;
             line-height: 1; margin-bottom: 4px; }}
.lat-value-edge  {{ color: {T['accent']}; }}
.lat-value-cloud {{ color: {T['muted']};  }}
.lat-unit  {{ font-family: 'Space Mono', monospace; font-size: 1rem; opacity: .45; }}
.lat-desc  {{ font-size: .73rem; color: {T['muted']}; margin-top: 8px; line-height: 1.5; }}

.speedup-card {{
    background: rgba(30, 58, 98, 0.7);
    border: 2px solid rgba(30, 58, 98, 1);
    box-shadow: 0 5px 5px rgba(30, 30, 30, 0.5),
                0 0 0 1px rgb(30, 58, 98) inset;
    border-radius: 16px; padding: 1.6rem; text-align: center;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    height: 100%;
}}
.speedup-value {{
    font-family: 'Space Mono', monospace; font-size: 3.2rem; font-weight: 700;
    color: {T['accent']}; line-height: 1;
}}

/* ── Alertes ── */
.alert-pill {{
    background: {T['red']}0A; border: 1px solid {T['red']}33;
    border-radius: 8px; padding: .6rem 1rem; margin-bottom: .5rem;
    font-size: .82rem; display: flex; justify-content: space-between;
}}
.alert-type {{ color: {T['red']}; font-family: 'Space Mono', monospace; font-size: .7rem; }}
.alert-val  {{ color: {T['text']}; }}
.alert-time {{ color: {T['muted']}; font-size: .7rem; }}

.fancy-divider {{
    height: 1px; background: {T['divider']}; margin: 1.5rem 0;
}}
</style>
""", unsafe_allow_html=True)

# ── Mesures de latence ─────────────────────────────────────────────────────────
def measure_edge_latency(n=5):
    latencies = []
    for _ in range(n):
        try:
            t0 = time.time()
            requests.get(f"{MICRO_B}/health", timeout=5)
            latencies.append((time.time() - t0) * 1000)
            time.sleep(0.05)
        except Exception:
            pass
    return sum(latencies) / len(latencies) if latencies else None

def measure_cloud_latency(n=5):
    latencies = []
    for _ in range(n):
        try:
            t0 = time.time()
            requests.get(f"{API_URL}/health", timeout=10)
            latencies.append((time.time() - t0) * 1000)
            time.sleep(0.1)
        except Exception:
            pass
    return sum(latencies) / len(latencies) if latencies else None

# ── Data fetchers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=20)
def fetch_cloud_data(limit=300):
    try:
        r = requests.get(f"{API_URL}/data", params={"limit": limit},
                         headers=HEADERS, timeout=10)
        r.raise_for_status()
        df = pd.DataFrame(r.json())
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], format='mixed')
            df = df.sort_values("timestamp").reset_index(drop=True)
        return df, None
    except Exception as e:
        return pd.DataFrame(), str(e)

@st.cache_data(ttl=20)
def fetch_alerts(limit=20):
    try:
        r = requests.get(f"{MICRO_B}/alertes", params={"limit": limit}, timeout=4)
        return r.json().get("alertes", [])
    except Exception:
        return []

@st.cache_data(ttl=20)
def fetch_b_health():
    try:
        r = requests.get(f"{MICRO_B}/health", timeout=3)
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=20)
def fetch_cloud_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        return r.json()
    except Exception:
        return None

# ── Historique latences ────────────────────────────────────────────────────────
if "latency_history" not in st.session_state:
    st.session_state.latency_history = []

# ── Plotly layout dynamique ────────────────────────────────────────────────────
def base_layout():
    return dict(
        paper_bgcolor=T['plot_bg'],
        plot_bgcolor=T['plot_bg'],
        font=dict(family="DM Sans", color=T['chart_font'], size=11),
        margin=dict(l=0, r=10, t=30, b=0),
        hovermode="x unified",
        xaxis=dict(gridcolor=T['chart_grid'], showgrid=True, zeroline=False,
                   tickfont=dict(size=10, color=T['chart_font'])),
        yaxis=dict(gridcolor=T['chart_grid'], showgrid=True, zeroline=False,
                   tickfont=dict(size=10, color=T['chart_font'])),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10, color=T['chart_font'])),
    )

def line_chart(df, y, title, unit="", threshold=None, threshold_label=""):
    """Toutes les courbes de capteurs utilisent la même couleur accent."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df[y],
        mode="lines",
        line=dict(color=C_EDGE, width=2),
        fill="tozeroy",
        fillcolor="rgba(0,212,255,0.07)" if dark else "rgba(29,78,216,0.07)",
        name=title,
        hovertemplate=f"<b>%{{y:.2f}} {unit}</b><br>%{{x|%H:%M:%S}}<extra></extra>",
    ))
    if threshold is not None:
        fig.add_hline(y=threshold, line_dash="dash", line_color=C_ALERT,
                      line_width=1.5, opacity=0.7,
                      annotation_text=threshold_label,
                      annotation_font=dict(size=9, color=C_ALERT))
    fig.update_layout(**base_layout(),
        title=dict(text=title, font=dict(size=12, color=T['chart_title']), x=0))
    fig.update_xaxes(tickformat="%H:%M")
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════
now_utc   = datetime.now(timezone.utc)
now_str   = now_utc.strftime("%Y-%m-%d  %H:%M:%S UTC")

with st.spinner("Mesure des latences en cours…"):
    edge_lat  = measure_edge_latency()
    cloud_lat = measure_cloud_latency()

df, err   = fetch_cloud_data()
alerts    = fetch_alerts()
b_health  = fetch_b_health()
c_health  = fetch_cloud_health()

if not df.empty:
    cutoff_2h    = now_utc - timedelta(hours=2)
    cutoff_naive = cutoff_2h.replace(tzinfo=None)
    df_2h = df[df["timestamp"] >= cutoff_naive].copy()
    if df_2h.empty:
        df_2h = df.copy()
else:
    df_2h = pd.DataFrame()

if edge_lat and cloud_lat:
    st.session_state.latency_history.append(
        {"ts": now_utc, "edge": edge_lat, "cloud": cloud_lat})
    st.session_state.latency_history = st.session_state.latency_history[-60:]
lat_df = pd.DataFrame(st.session_state.latency_history)

# ══════════════════════════════════════════════════════════════════════════════
# BANNER FIXE — menubar avec bouton toggle au centre
# ══════════════════════════════════════════════════════════════════════════════
edge_ok   = edge_lat  is not None
cloud_ok  = cloud_lat is not None
sys_ok    = edge_ok and cloud_ok and not df.empty
sys_label = "SYSTÈME OPÉRATIONNEL" if sys_ok else "DÉGRADÉ — vérifier les services"
sys_color = T['green'] if sys_ok else T['red']

# ── Banner HTML pur fixe (indépendant de Streamlit) ──────────────────────────
st.markdown(f"""
<div id="edgepulse-banner">
  <div>
    <div class="banner-title">EdgePulse Dashboard</div>
    <div class="banner-sub">Projet 09 · G09 · ENSA Tétouan · Edge vs Cloud</div>
  </div>
  <!-- zone centrale vide : le bouton Streamlit s'y superpose via #banner-toggle-anchor -->
  <div style="flex:1"></div>
  <div style="text-align:right;flex-shrink:0">
    <div class="banner-status" style="color:{sys_color}">
      <span class="banner-dot" style="background:{sys_color};box-shadow:0 0 10px {sys_color}"></span>
      {sys_label}
    </div>
    <div style="font-size:0.66rem;color:{'#64748B' if dark else 'rgba(255,255,255,0.65)'};
                margin-top:3px;font-family:'Space Mono',monospace">{now_str}</div>
  </div>
</div>""", unsafe_allow_html=True)

# Bouton toggle : rendu par Streamlit dans un div ancré en CSS fixed au centre du banner
if st.button(f"{T['toggle_icon']}  {'Mode clair' if dark else 'Mode sombre'}",
             key="theme_toggle", help=T['toggle_label']):
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — LATENCE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">01 — Comparaison de Latence en Temps Réel (mesurée)</div>',
            unsafe_allow_html=True)

# Conteneur flex pour aligner verticalement les 4 éléments
st.markdown('<div class="lat-section">', unsafe_allow_html=True)
col_e, col_c, col_s, col_bar = st.columns([1.2, 1.2, 1.2, 2.4])

with col_e:
    e_str = f"{edge_lat:.1f}" if edge_lat else "—"
    st.markdown(f"""
    <div class="lat-card">
      <div><span class="lat-badge lat-badge-edge">Edge · Local</span></div>
      <div class="lat-value lat-value-edge">{e_str}<span class="lat-unit"> ms</span></div>
      <div class="lat-desc">Microservice B — traitement local<br>Raspberry Pi 5 · ARM64</div>
    </div>""", unsafe_allow_html=True)

with col_c:
    cl_str = f"{cloud_lat:.0f}" if cloud_lat else "—"
    st.markdown(f"""
    <div class="lat-card">
      <div><span class="lat-badge lat-badge-cloud">Cloud · Azure</span></div>
      <div class="lat-value lat-value-cloud">{cl_str}<span class="lat-unit"> ms</span></div>
      <div class="lat-desc">API Azure · South Africa North<br>Tétouan — Johannesburg</div>
    </div>""", unsafe_allow_html=True)

with col_s:
    if edge_lat and cloud_lat:
        ratio_str = f"{cloud_lat / edge_lat:.0f}"
        reduction = f"{((cloud_lat - edge_lat) / cloud_lat * 100):.0f}%"
        extra     = f'<span style="color:{T["accent"]};font-size:.7rem">Latence réduite de {reduction}</span>'
    else:
        ratio_str, extra = "—", ""
    st.markdown(f"""
    <div class="speedup-card">
      <div style="font-size:.62rem;letter-spacing:.2em;text-transform:uppercase;
                  color:{T['muted']};margin-bottom:.8rem;font-family:'Space Mono',monospace">Gain Edge</div>
      <div class="speedup-value">{ratio_str}×</div>
      <div style="font-size:.72rem;color:{T['muted']};margin-top:10px;line-height:1.6">
        plus rapide que le Cloud<br>{extra}
      </div>
    </div>""", unsafe_allow_html=True)

with col_bar:
    if edge_lat and cloud_lat:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["Edge (Local)", "Cloud (Azure)"],
            y=[edge_lat, cloud_lat],
            marker_color=[C_EDGE, "#FF6B35"],
            marker_line_width=0,
            text=[f"{edge_lat:.1f} ms", f"{cloud_lat:.0f} ms"],
            textposition="outside",
            textfont=dict(family="Space Mono", size=11, color=T['text']),
            width=0.4,
        ))
        fig_bar.add_hline(y=10, line_dash="dot", line_color=C_ALERT, line_width=1.5,
                          annotation_text="Seuil : 10 ms",
                          annotation_font=dict(size=9, color=C_ALERT))
        fig_bar.update_layout(
            height=300,
            paper_bgcolor=T['plot_bg'], plot_bgcolor=T['plot_bg'],
            font=dict(family="DM Sans", color=T['chart_font'], size=11),
            margin=dict(l=0, r=10, t=30, b=0),
            title=dict(text="Latence comparée (ms) — échelle log",
                       font=dict(size=11, color=T['chart_title']), x=0),
            xaxis=dict(gridcolor=T['chart_grid'], tickfont=dict(size=10, color=T['chart_font'])),
            yaxis=dict(type="linear", tickvals=[1, 100, 400, 900, 1500], gridcolor=T['chart_grid'],
                       tickfont=dict(size=10, color=T['chart_font'])),
            showlegend=False, bargap=0.4,
        )
        st.plotly_chart(fig_bar, width='stretch', config={"displayModeBar": False})

st.markdown('</div>', unsafe_allow_html=True)

# (alignement vertical géré via height:100% dans les classes CSS des cartes)

# ── Historique latences session ────────────────────────────────────────────────
if len(lat_df) >= 2:
    st.markdown('<div class="section-label" style="margin-top:1rem">Evolution des latences sur la session</div>',
                unsafe_allow_html=True)
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=lat_df["ts"], y=lat_df["edge"],
        mode="lines", name="Edge",
        line=dict(color=C_EDGE, width=2),
        hovertemplate="<b>Edge : %{y:.1f} ms</b><br>%{x|%H:%M:%S}<extra></extra>",
    ))
    fig_hist.add_trace(go.Scatter(
        x=lat_df["ts"], y=lat_df["cloud"],
        mode="lines", name="Cloud",
        line=dict(color=C_CLOUD, width=2),
        hovertemplate="<b>Cloud : %{y:.0f} ms</b><br>%{x|%H:%M:%S}<extra></extra>",
    ))
    fig_hist.add_hline(y=10, line_dash="dot", line_color=C_ALERT, line_width=1,
                       annotation_text="10 ms",
                       annotation_font=dict(size=8, color=C_ALERT))
    fig_hist.update_layout(**base_layout(),
        title=dict(text="Historique Edge vs Cloud (session en cours)",
                   font=dict(size=12, color=T['chart_title']), x=0))
    fig_hist.update_xaxes(tickformat="%H:%M:%S")
    st.plotly_chart(fig_hist, width='stretch', config={"displayModeBar": False})

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — KPI
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">02 — Dernière Mesure Reçue (Cloud)</div>',
            unsafe_allow_html=True)

if not df.empty:
    last     = df.iloc[-1]
    temp_min = df["temperature"].min()
    temp_max = df["temperature"].max()
    temp_avg = df["temperature"].mean()

    kpis = [
        (f"{last['temperature']:.1f}", "°C",  "Temperature",  last["temperature"] >= 30),
        (f"{last['humidity']:.1f}",    "%",   "Humidite",     False),
        (f"{last['pressure']:.1f}",   "hPa",  "Pression",     False),
        (f"{last['voltage']:.2f}",     "V",   "Tension",      last["voltage"] < 2.5),
        (f"{last['current']:.2f}",     "A",   "Courant",      last["current"] > 3.0),
        (str(len(df)),               "pts",   "Mesures Cloud", False),
    ]
    cols = st.columns(6)
    for col, (val, unit, label, alerte) in zip(cols, kpis):
        with col:
            note = f'<div style="font-size:.65rem;color:{T["red"]};margin-top:6px">SEUIL DEPASSE</div>' if alerte else ""
            st.markdown(f"""
            <div class="kpi-card">
              <div class="kpi-value">{val}<span class="kpi-unit"> {unit}</span></div>
              <div class="kpi-label">{label}</div>{note}
            </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{T['stats_bg']};border:1px solid {T['border']};border-radius:10px;
                padding:.8rem 1.5rem;margin-top:.5rem;display:flex;gap:2rem;flex-wrap:wrap;
                font-family:'Space Mono',monospace;font-size:.75rem;color:{T['muted']}">
      <span>MIN : <b style="color:{T['accent']}">{temp_min:.1f} C</b></span>
      <span>MAX : <b style="color:{T['text']}">{temp_max:.1f} C</b></span>
      <span>MOYENNE : <b style="color:{T['text']}">{temp_avg:.1f} C</b></span>
      <span>MAJ : <b style="color:{T['text']}">{str(last['timestamp'])[:19]}</b></span>
      <span>DEVICE : <b style="color:{T['accent']}">{last.get('device_id','—')}</b></span>
    </div>""", unsafe_allow_html=True)
else:
    st.warning(f"Aucune donnée cloud : {err}")

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — GRAPHIQUES HISTORIQUES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div class="section-label">03 — Historique des Capteurs — 2 dernières heures '
    f'({len(df_2h)} mesures / {len(df)} totales)</div>',
    unsafe_allow_html=True)

if not df_2h.empty:
    r1a, r1b = st.columns(2)
    with r1a:
        st.plotly_chart(
            line_chart(df_2h, "temperature", "Temperature (°C)", "°C",
                       threshold=30, threshold_label="Seuil : 30°C"),
            width='stretch', config={"displayModeBar": False})
    with r1b:
        st.plotly_chart(
            line_chart(df_2h, "humidity", "Humidite (%)", "%"),
            width='stretch', config={"displayModeBar": False})

    r2a, r2b = st.columns(2)
    with r2a:
        st.plotly_chart(
            line_chart(df_2h, "pressure", "Pression (hPa)", "hPa",
                       threshold=950, threshold_label="Min : 950 hPa"),
            width='stretch', config={"displayModeBar": False})
    with r2b:
        try:
            if "acceleration" in df_2h.columns and isinstance(df_2h["acceleration"].iloc[0], dict):
                df_2h["acc_x"] = df_2h["acceleration"].apply(lambda d: d.get("x", 0))
                df_2h["acc_y"] = df_2h["acceleration"].apply(lambda d: d.get("y", 0))
                df_2h["acc_z"] = df_2h["acceleration"].apply(lambda d: d.get("z", 0))
            if "acc_x" in df_2h.columns:
                # Accélération : 3 axes en niveaux d'opacité du même accent
                alpha_colors = (
                    ["#00D4FF", "rgba(0,212,255,0.55)", "rgba(0,212,255,0.25)"]
                    if dark else
                    ["#1D4ED8", "rgba(29,78,216,0.55)", "rgba(29,78,216,0.25)"]
                )
                fig_acc = go.Figure()
                for (axis, col_color) in zip(["acc_x","acc_y","acc_z"], alpha_colors):
                    fig_acc.add_trace(go.Scatter(
                        x=df_2h["timestamp"], y=df_2h[axis],
                        mode="lines", name=f"Axe {axis[-1].upper()}",
                        line=dict(color=col_color, width=1.8),
                        hovertemplate=f"<b>%{{y:.3f}} m/s²</b><extra>Axe {axis[-1].upper()}</extra>",
                    ))
                fig_acc.update_layout(**base_layout(),
                    title=dict(text="Acceleration (m/s²) — 3 axes",
                               font=dict(size=12, color=T['chart_title']), x=0))
                fig_acc.update_xaxes(tickformat="%H:%M")
                st.plotly_chart(fig_acc, width='stretch',
                                config={"displayModeBar": False})
        except Exception:
            st.info("Données d'accélération non disponibles.")

    r3a, r3b = st.columns(2)
    with r3a:
        st.plotly_chart(
            line_chart(df_2h, "voltage", "Tension (V)", "V",
                       threshold=2.5, threshold_label="Min : 2.5V"),
            width='stretch', config={"displayModeBar": False})
    with r3b:
        st.plotly_chart(
            line_chart(df_2h, "current", "Courant (A)", "A"),
            width='stretch', config={"displayModeBar": False})
else:
    st.info("Aucune donnée dans les 2 dernières heures.")

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ALERTES & SERVICES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">04 — Alertes Edge et Etat des Services</div>',
            unsafe_allow_html=True)
col_al, col_st = st.columns([1.5, 1])

with col_al:
    st.markdown("**Dernières alertes (Microservice B)**")
    if alerts:
        for a in alerts[:8]:
            ts = a.get("timestamp", "")[:19].replace("T", " ")
            st.markdown(f"""
            <div class="alert-pill">
              <div>
                <div class="alert-type">{a.get('type','—')} · {a.get('capteur','—')}</div>
                <div class="alert-val">{a.get('message','—')}</div>
              </div>
              <div class="alert-time">{ts}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:{T['accent']}0A;border:1px solid {T['accent']}22;
                    border-radius:10px;padding:1rem;text-align:center;
                    color:{T['muted']};font-size:.85rem">
          Aucune alerte active — tous les capteurs dans les seuils normaux
        </div>""", unsafe_allow_html=True)

with col_st:
    st.markdown("**Etat des Services**")
    b_detail = (f"Buffer : {b_health.get('buffer_taille',0)} · "
                f"Alertes : {b_health.get('total_alertes',0)} · "
                f"Agregats : {b_health.get('total_agregats',0)}"
                if b_health else "Inaccessible")
    c_detail = (f"Latence : {cloud_lat:.0f} ms · Status : {c_health.get('status','?')}"
                if cloud_lat and c_health else "Timeout")
    svcs = [
        ("Microservice B (Edge)",   edge_ok,     b_detail),
        ("API Cloud (Azure)",       cloud_ok,    c_detail),
        ("Base de données (Cloud)", not df.empty,
         f"{len(df)} enregistrement(s) · id max = {df['id'].max() if not df.empty else '—'}"),
        ("Microservice C (Sync)",   True,        "Synchronisation toutes les 5 min"),
    ]
    for name, ok, detail in svcs:
        dot = T['green'] if ok else T['red']
        st.markdown(f"""
        <div style="background:{T['svc_bg']};border:1px solid {T['border']};
                    border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem;
                    display:flex;align-items:center;gap:12px">
          <div style="width:8px;height:8px;border-radius:50%;background:{dot};
                      box-shadow:0 0 8px {dot};flex-shrink:0"></div>
          <div>
            <div style="font-size:.82rem;font-weight:600;color:{T['text']}">{name}</div>
            <div style="font-size:.7rem;color:{T['muted']};margin-top:2px">{detail}</div>
          </div>
        </div>""", unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — TABLEAU
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">05 — Données Brutes (Cloud · 15 dernières mesures)</div>',
            unsafe_allow_html=True)

if not df.empty:
    show_cols = [c for c in ["id", "timestamp", "temperature", "humidity",
                              "pressure", "voltage", "current", "device_id"]
                 if c in df.columns]
    disp = df[show_cols].tail(15).sort_values("id", ascending=False).reset_index(drop=True)
    disp["timestamp"] = disp["timestamp"].astype(str).str[:19]
    st.dataframe(disp, width='stretch', hide_index=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:2rem 0 .5rem;font-family:'Space Mono',monospace;
            font-size:.62rem;color:{T['footer_color']};letter-spacing:.1em;text-transform:uppercase">
  EDGEPULSE · PROJET 09 · G09 · ENSA TÉTOUAN · MAI 2026 · PROF. BENALY MOHAMED
  · ACTUALISATION AUTO 30S
</div>""", unsafe_allow_html=True)

time.sleep(30)
st.rerun()
