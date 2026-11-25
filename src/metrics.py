"""Cálculos de negocio: KPIs, agrupaciones y series temporales."""
import numpy as np
import pandas as pd

MONEDA = "$"


def fmt_money(v: float, decimales: int = 0) -> str:
    """Formatea dinero: 1 234 567 -> $1.23 M cuando es muy grande."""
    if abs(v) >= 1_000_000:
        return f"{MONEDA}{v / 1_000_000:,.2f} M"
    return f"{MONEDA}{v:,.{decimales}f}"


def kpis(df: pd.DataFrame) -> dict:
    """KPIs ejecutivos.

    Utilidad Bruta  = Ventas - Costos
    Margen Bruto %  = Utilidad Bruta / Ventas * 100
    Ticket Promedio = Ventas Totales / Número de Transacciones
    """
    ventas, costo = df["ventas"].sum(), df["costo"].sum()
    utilidad = ventas - costo
    trans = df["id_transaccion"].nunique()
    return {
        "ventas": ventas,
        "utilidad": utilidad,
        "margen": utilidad / ventas * 100 if ventas else 0.0,
        "ticket": ventas / trans if trans else 0.0,
        "clientes": df["id_cliente"].nunique(),
        "transacciones": trans,
    }


def agrupar(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Ventas, costo, utilidad, margen y participación por dimensión (orden: utilidad desc)."""
    g = df.groupby(col, dropna=False).agg(
        ventas=("ventas", "sum"), costo=("costo", "sum"), unidades=("cantidad", "sum"),
        transacciones=("id_transaccion", "nunique")).reset_index()
    g["utilidad"] = g["ventas"] - g["costo"]
    g["margen"] = np.where(g["ventas"] > 0, g["utilidad"] / g["ventas"] * 100, 0.0)
    total = g["ventas"].sum()
    g["participacion"] = g["ventas"] / total * 100 if total else 0.0
    return g.sort_values("utilidad", ascending=False).reset_index(drop=True)


def serie_temporal(df: pd.DataFrame, freq: str = "MS") -> pd.DataFrame:
    """Ventas y utilidad por período. freq: 'D' diario, 'W' semanal, 'MS' mensual."""
    return (df.set_index("fecha")[["ventas", "utilidad"]].resample(freq).sum().reset_index())
