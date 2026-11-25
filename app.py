"""San Francisco Crust Pizza — Sistema Inteligente de Apoyo a la Toma de Decisiones.

Ejecutar:  streamlit run app.py
"""
import os
from pathlib import Path

import streamlit as st

from src import assistant as ai
from src import charts as ch
from src import data_loader as dl
from src import demo_data, insights as ins, metrics as mt

st.set_page_config(page_title="San Francisco Crust Pizza | Decisiones", page_icon="🍕", layout="wide")
st.markdown("""
<style>
.banner{background:linear-gradient(90deg,#C8102E,#8E0B21);color:#fff;padding:18px 26px;border-radius:10px;margin-bottom:14px}
.banner h1{margin:0;font-size:1.7rem;color:#fff}.banner p{margin:2px 0 0;opacity:.9}
.kpi{background:#fff;border-radius:10px;padding:14px 16px;border-left:6px solid #C8102E;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.kpi .t{font-size:.78rem;color:#6B7280;text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:1.65rem;font-weight:700;color:#1F2937}
h3{border-bottom:2px solid #F2A900;padding-bottom:4px}
</style>""", unsafe_allow_html=True)

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data(show_spinner="Procesando datos…")
def preparar(archivos: dict):
    """Lee y une las tablas. Se recalcula solo cuando cambian los archivos (caché)."""
    if archivos:
        tablas = {rol: dl.leer_archivo(n, b) for rol, (n, b) in archivos.items()}
    else:
        tablas = demo_data.generar()
    return dl.construir_dataset(**tablas)


def clave_api():
    try:
        return st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        return os.getenv("OPENAI_API_KEY")


# ───────────────────────── Sidebar: datos ─────────────────────────
st.sidebar.markdown("## 🍕 San Francisco Crust Pizza")
subidos = st.sidebar.file_uploader("📂 Cargar datos (ventas, clientes, productos)", type=["csv", "xlsx"],
                                   accept_multiple_files=True,
                                   help="El nombre del archivo debe contener 'ventas', 'clientes' o 'productos'. "
                                        "Los archivos cargados reemplazan a los de la carpeta data/.")
archivos = {}
for p in sorted(DATA_DIR.glob("*")) if DATA_DIR.exists() else []:
    rol = dl.rol_por_nombre(p.name)
    if rol and p.suffix.lower() in (".csv", ".xlsx"):
        archivos[rol] = (p.name, p.read_bytes())
for f in subidos or []:
    rol = dl.rol_por_nombre(f.name)
    if rol:
        archivos[rol] = (f.name, f.getvalue())
    else:
        st.sidebar.warning(f"'{f.name}' no se reconoce (usa 'ventas', 'clientes' o 'productos' en el nombre).")

if archivos and "ventas" not in archivos:
    st.error("Falta el archivo de ventas.")
    st.stop()
try:
    df, avisos, mapeos = preparar(archivos)
except ValueError as e:
    st.error(str(e))
    st.stop()
if not archivos:
    st.info("Mostrando **datos de demostración**. Carga tus archivos en la barra lateral para ver tu negocio.")

# ───────────────────────── Sidebar: filtros ─────────────────────────
st.sidebar.markdown("### 🔎 Filtros")
fmin, fmax = df.fecha.min().date(), df.fecha.max().date()
rango = st.sidebar.date_input("Fecha", (fmin, fmax), min_value=fmin, max_value=fmax)
sel = {c: st.sidebar.multiselect(etq, sorted(df[c].unique()), placeholder="Todas")
       for c, etq in (("ciudad", "Ciudad"), ("sucursal", "Sucursal"), ("segmento", "Segmento de cliente"), ("producto", "Producto"))}

dff = df
if isinstance(rango, (tuple, list)) and len(rango) == 2:
    dff = dff[(dff.fecha.dt.date >= rango[0]) & (dff.fecha.dt.date <= rango[1])]
for c, valores in sel.items():
    if valores:
        dff = dff[dff[c].isin(valores)]
filtros_txt = "; ".join(f"{c}: {', '.join(map(str, v))}" for c, v in sel.items() if v)

with st.sidebar.expander("🧩 Esquema detectado y avisos"):
    for t, m in mapeos.items():
        st.caption(f"**{t}**: " + ", ".join(f"{k}←{v}" for k, v in m.items()))
    for a in avisos:
        st.warning(a)
with st.sidebar.expander("🤖 Configuración de IA"):
    api_key = st.text_input("OpenAI API key", value=clave_api() or "", type="password")
    modelo = st.text_input("Modelo", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    base_url = st.text_input("Base URL (opcional)", value=os.getenv("OPENAI_BASE_URL", ""))

st.markdown('<div class="banner"><h1>🍕 San Francisco Crust Pizza</h1>'
            '<p>Sistema Inteligente de Apoyo a la Toma de Decisiones</p></div>', unsafe_allow_html=True)
if dff.empty:
    st.warning("Los filtros actuales no devuelven datos. Ajusta la selección.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📊 Dashboard ejecutivo", "🧭 Análisis estratégico", "🤖 Asistente IA"])

# ───────────────────────── Tab 1: dashboard ─────────────────────────
with tab1:
    k = mt.kpis(dff)
    tarjetas = [("Ventas totales", mt.fmt_money(k["ventas"])), ("Utilidad bruta", mt.fmt_money(k["utilidad"])),
                ("Margen bruto", f"{k['margen']:.1f}%"), ("Ticket promedio", mt.fmt_money(k["ticket"], 2)),
                ("Clientes", f"{k['clientes']:,}"), ("Transacciones", f"{k['transacciones']:,}")]
    for col, (t, v) in zip(st.columns(6), tarjetas):
        col.markdown(f'<div class="kpi"><div class="t">{t}</div><div class="v">{v}</div></div>', unsafe_allow_html=True)

    prod = mt.agrupar(dff, "producto")
    st.markdown("### Productos")
    a, b = st.columns(2)
    a.plotly_chart(ch.barras_h(prod.sort_values("unidades", ascending=False).head(10), "producto", "unidades",
                               "Top 10 productos más vendidos (unidades)", fmt=",.0f", color="#1F2937"))
    b.plotly_chart(ch.barras_h(prod.head(10), "producto", "utilidad", "Top 10 productos con mayor utilidad"))

    st.markdown("### Geografía y sucursales")
    a, b = st.columns(2)
    a.plotly_chart(ch.barras_v(mt.agrupar(dff, "ciudad"), "ciudad", "ventas", "Ventas por ciudad"))
    b.plotly_chart(ch.barras_v(mt.agrupar(dff, "sucursal"), "sucursal", "ventas", "Ventas por sucursal"))
    mapa = ch.mapa(dff)
    if mapa is not None:
        st.plotly_chart(mapa)
    else:
        st.caption("🗺️ Para ver el mapa, incluye columnas de latitud y longitud en clientes o ventas.")

    st.markdown("### Clientes y categorías")
    a, b = st.columns(2)
    a.plotly_chart(ch.dona(mt.agrupar(dff, "segmento"), "segmento", "ventas", "Ventas por segmento de cliente"))
    b.plotly_chart(ch.dona(mt.agrupar(dff, "categoria"), "categoria", "ventas", "Participación de ventas por categoría"))

    st.markdown("### Evolución temporal")
    freq = {"Diaria": "D", "Semanal": "W", "Mensual": "MS"}[st.radio("Granularidad", ["Diaria", "Semanal", "Mensual"], index=2, horizontal=True)]
    ts = mt.serie_temporal(dff, freq)
    a, b = st.columns(2)
    a.plotly_chart(ch.linea(ts, "ventas", "Evolución de ventas"))
    b.plotly_chart(ch.linea(ts, "utilidad", "Evolución de utilidad", color="#2E7D32", area=True))

# ───────────────────────── Tab 2: análisis estratégico ─────────────────────────
with tab2:
    st.markdown("### 🔑 Los 5 hallazgos más importantes")
    for i, h in enumerate(ins.hallazgos(dff), 1):
        st.markdown(f"{i}. {h}")
    mejor, peor = ins.mejor_peor_sucursal(dff)
    a, b = st.columns(2)
    if mejor is not None:
        a.metric("🏆 Mejor sucursal", mejor.sucursal, f"{mt.fmt_money(mejor.utilidad)} utilidad · {mejor.margen:.1f}% margen")
        b.metric("⚠️ Peor sucursal", peor.sucursal, f"{mt.fmt_money(peor.utilidad)} utilidad · {peor.margen:.1f}% margen", delta_color="off")
    cols_t = {"producto": "Producto", "ventas": "Ventas", "utilidad": "Utilidad", "margen": "Margen %", "unidades": "Unidades"}
    a, b = st.columns(2)
    a.markdown("#### Productos más rentables")
    a.dataframe(ins.productos_rentables(dff)[list(cols_t)].rename(columns=cols_t), hide_index=True)
    b.markdown("#### Productos de bajo desempeño")
    b.dataframe(ins.productos_bajo_desempeno(dff)[list(cols_t)].rename(columns=cols_t), hide_index=True)
    seg, tabla = ins.segmento_potencial(dff)
    if seg is not None:
        st.markdown(f"#### Segmento con mayor potencial: **{seg.segmento}**")
        ren = {"segmento": "Segmento", "ventas": "Ventas", "margen": "Margen %", "participacion": "Participación %",
               "crecimiento": "Crecimiento %", "puntaje": "Puntaje"}
        st.dataframe(tabla[[c for c in ren if c in tabla]].rename(columns=ren), hide_index=True)
    st.markdown("### 🎯 Recomendaciones estratégicas")
    for r in ins.recomendaciones(dff):
        st.markdown(f"- {r}")

# ───────────────────────── Tab 3: asistente IA ─────────────────────────
with tab3:
    st.caption("Pregunta sobre los datos filtrados. Ej.: «¿Cuál es la sucursal más rentable?», «¿Qué productos debo promocionar?», «¿Qué segmento tiene mejor desempeño?»")
    if not api_key:
        st.info("Sin API key: el asistente responde con reglas locales. Añade tu key en la barra lateral para activar la IA generativa.")
    st.session_state.setdefault("chat", [])
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    if pregunta := st.chat_input("Escribe tu pregunta de negocio…"):
        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            with st.spinner("Analizando…"):
                resp = ai.responder(pregunta, dff, st.session_state.chat, filtros_txt, api_key or None, modelo, base_url)
            st.markdown(resp)
        st.session_state.chat += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": resp}]
