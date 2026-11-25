"""Análisis estratégico automático: hallazgos, rankings y recomendaciones basadas en reglas."""
import numpy as np
import pandas as pd

from .metrics import agrupar, fmt_money, kpis, serie_temporal


def mejor_peor_sucursal(df):
    """(mejor, peor) sucursal por utilidad bruta, como filas de pandas."""
    g = agrupar(df, "sucursal")
    return (g.iloc[0], g.iloc[-1]) if len(g) else (None, None)


def productos_rentables(df, n=5):
    """Productos con mayor utilidad bruta."""
    return agrupar(df, "producto").head(n)


def productos_bajo_desempeno(df, n=5):
    """Productos en el cuartil inferior de utilidad o de margen (los n peores por utilidad)."""
    g = agrupar(df, "producto")
    if len(g) < 4:
        return g.tail(n).iloc[::-1]
    cand = g[(g.utilidad <= g.utilidad.quantile(.25)) | (g.margen <= g.margen.quantile(.25))]
    return cand.nsmallest(n, "utilidad")


def productos_a_promocionar(df, n=5):
    """Alto margen (>= mediana) y bajo volumen (<= mediana de unidades): potencial no explotado."""
    g = agrupar(df, "producto")
    cand = g[(g.margen >= g.margen.median()) & (g.unidades <= g.unidades.median())]
    return cand.nlargest(n, "margen")


def segmento_potencial(df):
    """Segmento con mayor potencial de crecimiento.

    Puntaje = 50% crecimiento (2ª mitad del período vs 1ª) + 30% margen + 20% espacio
    de crecimiento (menor participación actual). Devuelve (fila_ganadora, tabla).
    """
    g = agrupar(df, "segmento")
    if len(g) <= 1:
        return (g.iloc[0] if len(g) else None), g
    corte = df["fecha"].min() + (df["fecha"].max() - df["fecha"].min()) / 2
    a = df[df.fecha <= corte].groupby("segmento")["ventas"].sum()
    b = df[df.fecha > corte].groupby("segmento")["ventas"].sum()
    g["crecimiento"] = g["segmento"].map((b - a) / a.replace(0, np.nan) * 100).fillna(0)
    g["puntaje"] = (g.crecimiento.rank(pct=True) * .5 + g.margen.rank(pct=True) * .3
                    + (1 - g.participacion.rank(pct=True)) * .2)
    g = g.sort_values("puntaje", ascending=False).reset_index(drop=True)
    return g.iloc[0], g


def hallazgos(df, n=5):
    """Los hallazgos más relevantes en texto (máx. n)."""
    h = []
    mejor, peor = mejor_peor_sucursal(df)
    if mejor is not None and mejor.sucursal != peor.sucursal:
        h.append(f"**{mejor.sucursal}** es la sucursal más rentable ({fmt_money(mejor.utilidad)} de utilidad, "
                 f"{mejor.margen:.1f}% de margen); **{peor.sucursal}** la menos rentable ({fmt_money(peor.utilidad)}, {peor.margen:.1f}%).")
    prod = agrupar(df, "producto")
    if len(prod) >= 3 and prod.utilidad.sum() > 0:
        top = prod.head(3)
        h.append(f"Concentración: {', '.join(top['producto'])} generan el {top.utilidad.sum() / prod.utilidad.sum() * 100:.0f}% de la utilidad bruta.")
    bajo = productos_bajo_desempeno(df, 3)
    if len(bajo) and len(prod) >= 4:
        h.append(f"Bajo desempeño: {', '.join(bajo['producto'])} están en el cuartil inferior de utilidad o margen.")
    cat = agrupar(df, "categoria")
    if len(cat) > 1:
        c = cat.sort_values("margen", ascending=False)
        h.append(f"La categoría **{c.iloc[0].categoria}** tiene el mejor margen ({c.iloc[0].margen:.1f}%) y **{c.iloc[-1].categoria}** el peor ({c.iloc[-1].margen:.1f}%).")
    ts = serie_temporal(df, "MS")
    if len(ts) >= 3 and ts.ventas.iloc[-2] > 0:
        var = (ts.ventas.iloc[-1] / ts.ventas.iloc[-2] - 1) * 100
        h.append(f"Tendencia: el último mes del filtro varía {var:+.1f}% frente al anterior (puede estar incompleto).")
    seg, _ = segmento_potencial(df)
    if seg is not None:
        h.append(f"El segmento con mayor potencial es **{seg.segmento}** (margen {seg.margen:.1f}%, {seg.participacion:.1f}% de las ventas).")
    return h[:n]


def recomendaciones(df):
    """Recomendaciones estratégicas derivadas de los datos filtrados."""
    r, k = [], kpis(df)
    promo = productos_a_promocionar(df, 3)
    if len(promo):
        r.append(f"**Promocionar** {', '.join(promo['producto'])}: margen alto con volumen bajo; combos y destacados en carta/app.")
    bajo = productos_bajo_desempeno(df, 3)
    if len(bajo) and len(agrupar(df, "producto")) >= 4:
        r.append(f"**Revisar** {', '.join(bajo['producto'])}: ajustar precio o costo, reformular receta o retirar de la carta.")
    mejor, peor = mejor_peor_sucursal(df)
    if mejor is not None and mejor.sucursal != peor.sucursal:
        r.append(f"**Replicar** las prácticas de {mejor.sucursal} (mix de productos, horarios, servicio) en {peor.sucursal}, que está {mejor.margen - peor.margen:.1f} pp por debajo en margen.")
    seg, _ = segmento_potencial(df)
    if seg is not None:
        r.append(f"**Campaña dirigida** al segmento {seg.segmento}: programas de fidelidad y ofertas para aumentar su frecuencia de compra.")
    r.append(f"**Subir el ticket promedio** ({fmt_money(k['ticket'], 2)}) con combos pizza + bebida/postre y venta sugerida en caja.")
    return r
