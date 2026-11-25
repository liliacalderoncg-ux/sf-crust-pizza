"""Gráficos Plotly con estilo corporativo (rojo tomate, carbón, dorado queso, verde albahaca)."""
import plotly.express as px

# Coordenadas de respaldo (ciudad -> lat, lon) cuando los datos no incluyen latitud/longitud.
# Añade aquí nuevas ciudades si aparecen en tus archivos.
COORDENADAS = {"Dallas": (32.7767, -96.7970), "Houston": (29.7604, -95.3698),
               "Austin": (30.2672, -97.7431), "San Antonio": (29.4241, -98.4936)}
PALETA = ["#C8102E", "#1F2937", "#F2A900", "#2E7D32", "#8D6E63", "#5C6BC0", "#00897B", "#E57373"]


def _estilo(fig, titulo, alto=380):
    fig.update_layout(
        title=dict(text=titulo, x=0.01, font=dict(size=16)), template="plotly_white", height=alto,
        margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="white", plot_bgcolor="white",
        legend_title_text="", colorway=PALETA, font=dict(family="Segoe UI, Arial"))
    return fig


def barras_h(g, y, x, titulo, fmt="$,.0f", color=None):
    """Barras horizontales ordenadas (rankings)."""
    fig = px.bar(g.sort_values(x), x=x, y=y, orientation="h", text=x, color_discrete_sequence=[color or PALETA[0]])
    fig.update_traces(texttemplate="%{text:" + fmt + "}", textposition="outside", cliponaxis=False)
    fig.update_xaxes(title=None, showgrid=False, visible=False)
    fig.update_yaxes(title=None)
    return _estilo(fig, titulo)


def barras_v(g, x, y, titulo, fmt="$,.0f"):
    fig = px.bar(g.sort_values(y, ascending=False), x=x, y=y, text=y, color=x, color_discrete_sequence=PALETA)
    fig.update_traces(texttemplate="%{text:" + fmt + "}", textposition="outside", cliponaxis=False)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, showgrid=True, gridcolor="#EEE", visible=False)
    return _estilo(fig, titulo)


def dona(g, nombres, valores, titulo):
    fig = px.pie(g, names=nombres, values=valores, hole=0.55, color_discrete_sequence=PALETA)
    fig.update_traces(textinfo="percent+label", textposition="outside")
    fig.update_layout(showlegend=False)
    return _estilo(fig, titulo)


def linea(ts, y, titulo, color=None, area=False):
    fn = px.area if area else px.line
    fig = fn(ts, x="fecha", y=y, color_discrete_sequence=[color or PALETA[0]])
    fig.update_traces(hovertemplate="%{x|%d %b %Y}<br>%{y:$,.0f}<extra></extra>")
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, gridcolor="#EEE", tickprefix="$")
    return _estilo(fig, titulo)


def mapa(df):
    """Mapa de ventas por ciudad. Requiere columnas latitud/longitud; si no existen devuelve None."""
    if not {"latitud", "longitud"} <= set(df.columns) or df["latitud"].notna().sum() == 0:
        df = df.assign(latitud=df["ciudad"].map(lambda c: COORDENADAS.get(c, (None, None))[0]),
                       longitud=df["ciudad"].map(lambda c: COORDENADAS.get(c, (None, None))[1]))
        if df["latitud"].notna().sum() == 0:
            return None
    g = (df.dropna(subset=["latitud", "longitud"]).groupby("ciudad")
         .agg(ventas=("ventas", "sum"), lat=("latitud", "mean"), lon=("longitud", "mean")).reset_index())
    fig = px.scatter_geo(g, lat="lat", lon="lon", size="ventas", hover_name="ciudad",
                         hover_data={"ventas": ":$,.0f", "lat": False, "lon": False},
                         color_discrete_sequence=[PALETA[0]], size_max=45)
    fig.update_geos(fitbounds="locations", showcountries=True, countrycolor="#CCC", landcolor="#F7F5F2")
    return _estilo(fig, "Mapa de ventas por ciudad", 420)
