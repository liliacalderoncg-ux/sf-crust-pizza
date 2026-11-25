"""Asistente de IA sobre los datos filtrados.

Usa la API de OpenAI (o cualquier proveedor compatible vía base_url). Si no hay
API key, responde con reglas locales basadas en insights.py, así la app nunca se rompe.
"""
from . import insights as ins
from .metrics import agrupar, fmt_money, kpis, serie_temporal

SYSTEM = ("Eres el analista de negocio de la cadena 'San Francisco Crust Pizza'. Responde en español, de forma "
          "concisa y accionable, usando SOLO los datos del contexto (están ya filtrados por el usuario). Cita cifras "
          "exactas, justifica tus conclusiones y, si falta información para responder, dilo. Puedes proponer "
          "estrategias de crecimiento, promociones y acciones correctivas apoyadas en los datos.")


def construir_contexto(df, filtros_txt=""):
    """Resumen compacto de los datos filtrados para enviar al modelo."""
    k = kpis(df)
    partes = [f"Filtros activos: {filtros_txt or 'ninguno'}",
              f"Período: {df.fecha.min():%Y-%m-%d} a {df.fecha.max():%Y-%m-%d}",
              f"KPIs: ventas {fmt_money(k['ventas'])}, utilidad {fmt_money(k['utilidad'])}, margen {k['margen']:.1f}%, "
              f"ticket {fmt_money(k['ticket'], 2)}, clientes {k['clientes']}, transacciones {k['transacciones']}"]
    cols = ["ventas", "utilidad", "margen", "unidades"]
    for col in ("sucursal", "ciudad", "segmento", "categoria"):
        g = agrupar(df, col)[[col] + cols].round(1)
        partes.append(f"\n## Por {col}\n{g.head(15).to_string(index=False)}")
    p = agrupar(df, "producto")[["producto"] + cols].round(1)
    partes.append(f"\n## Productos con más utilidad\n{p.head(10).to_string(index=False)}")
    partes.append(f"\n## Productos con menos utilidad\n{p.tail(10).to_string(index=False)}")
    ts = serie_temporal(df, "MS").tail(18).round(0)
    ts["fecha"] = ts["fecha"].dt.strftime("%Y-%m")
    partes.append(f"\n## Evolución mensual\n{ts.to_string(index=False)}")
    return "\n".join(partes)


def responder_local(pregunta, df):
    """Respuestas basadas en reglas cuando no hay API key."""
    q = pregunta.lower()
    mejor, peor = ins.mejor_peor_sucursal(df)
    if "sucursal" in q and mejor is not None:
        if any(w in q for w in ("peor", "menos", "baja")):
            return f"La sucursal menos rentable es **{peor.sucursal}**: {fmt_money(peor.utilidad)} de utilidad y {peor.margen:.1f}% de margen."
        return f"La sucursal más rentable es **{mejor.sucursal}**: {fmt_money(mejor.utilidad)} de utilidad y {mejor.margen:.1f}% de margen."
    if any(w in q for w in ("promocion", "promover", "impulsar")):
        g = ins.productos_a_promocionar(df)
        return "Productos con buen margen y poco volumen, ideales para promocionar:\n" + "\n".join(
            f"- **{r.producto}** (margen {r.margen:.1f}%, {r.unidades:,.0f} unidades)" for r in g.itertuples()) if len(g) else "No hay productos que cumplan el criterio con los filtros actuales."
    if "segmento" in q:
        s, t = ins.segmento_potencial(df)
        return f"El segmento con mayor potencial es **{s.segmento}** (margen {s.margen:.1f}%, {s.participacion:.1f}% de las ventas)." if s is not None else "No hay datos de segmento."
    if any(w in q for w in ("bajo", "peor", "retirar")) and "producto" in q:
        g = ins.productos_bajo_desempeno(df)
        return "Productos de bajo desempeño:\n" + "\n".join(f"- **{r.producto}** (utilidad {fmt_money(r.utilidad)}, margen {r.margen:.1f}%)" for r in g.itertuples())
    return ("Sin API key de IA configurada solo puedo responder preguntas sobre sucursales, promociones, segmentos y "
            "productos de bajo desempeño. Hallazgos clave:\n" + "\n".join(f"- {h}" for h in ins.hallazgos(df)))


def responder(pregunta, df, historial, filtros_txt="", api_key=None, modelo="gpt-4o-mini", base_url=None):
    """Responde con IA generativa si hay API key; si no, con reglas locales."""
    if not api_key:
        return responder_local(pregunta, df)
    from openai import OpenAI
    cliente = OpenAI(api_key=api_key, base_url=base_url or None)
    msgs = [{"role": "system", "content": SYSTEM + "\n\nDATOS ACTUALES:\n" + construir_contexto(df, filtros_txt)}]
    msgs += historial[-8:] + [{"role": "user", "content": pregunta}]
    try:
        r = cliente.chat.completions.create(model=modelo, messages=msgs, temperature=0.2)
        return r.choices[0].message.content
    except Exception as e:
        return f"No pude consultar la IA ({e}). Respuesta local:\n\n{responder_local(pregunta, df)}"
