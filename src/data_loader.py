"""Carga, limpieza y unión de las tablas ventas / clientes / productos.

Diseño: el código NO depende de nombres exactos de columnas. Cada tabla se lee,
sus columnas se normalizan (sin tildes, minúsculas) y se asignan a un esquema
canónico mediante ALIASES. Si llegan archivos nuevos con la misma estructura (o
nombres equivalentes) todo se actualiza sin tocar el código. Si tu archivo usa
otros nombres, basta con añadirlos a ALIASES.

Formato numérico esperado: 1,234.56 (también admite "$" y comas decimales simples).
"""
import io
import re
import unicodedata
import warnings

import pandas as pd

# Esquema canónico -> nombres posibles (ya normalizados)
ALIASES = {
    "fecha": ["fecha", "fecha_venta", "fecha_pedido", "fecha_transaccion", "fecha_factura", "date", "dia"],
    "id_transaccion": ["id_venta", "id_transaccion", "id_pedido", "id_orden", "num_pedido", "numero_pedido",
                       "id_factura", "factura", "ticket", "order_id", "transaccion", "pedido", "n_pedido", "n_venta", "numero_venta", "num_venta", "venta_id"],
    "id_cliente": ["id_cliente", "cliente_id", "idcliente", "codigo_cliente", "cod_cliente", "customer_id"],
    "id_producto": ["id_producto", "producto_id", "idproducto", "codigo_producto", "cod_producto", "product_id", "sku"],
    "producto": ["producto", "nombre_producto", "nombre", "descripcion", "item", "product", "pizza"],
    "categoria": ["categoria", "category", "tipo_producto", "familia", "linea", "tipo"],
    "ciudad": ["ciudad", "city", "municipio"],
    "sucursal": ["sucursal", "tienda", "local", "punto_de_venta", "store", "branch", "restaurante"],
    "segmento": ["segmento", "segmento_cliente", "segment", "tipo_cliente"],
    "cantidad": ["cantidad", "unidades", "qty", "quantity", "cant"],
    "precio": ["precio", "precio_unitario", "precio_venta", "precio_venta_usd", "price", "unit_price"],
    "costo_unit": ["costo_unitario", "costo_unit", "unit_cost", "costo_producto"],
    "ventas": ["ventas", "venta", "venta_neta", "total_venta", "total", "importe", "monto", "ingreso", "ingresos",
               "revenue", "sales", "valor_total", "subtotal"],
    "costo": ["costo", "costos", "costo_total", "total_costo", "costo_venta", "cost", "cogs"],
    "latitud": ["latitud", "latitude", "lat"],
    "longitud": ["longitud", "longitude", "lon", "lng"],
}
# Qué campos puede aportar cada tabla
CAMPOS_POR_TABLA = {
    "ventas": ["fecha", "id_transaccion", "id_cliente", "id_producto", "cantidad", "precio", "ventas", "costo",
               "costo_unit", "sucursal", "ciudad", "producto", "categoria", "segmento", "latitud", "longitud"],
    "clientes": ["id_cliente", "ciudad", "segmento", "latitud", "longitud"],
    "productos": ["id_producto", "producto", "categoria", "precio", "costo_unit"],
}
# Alias adicionales válidos solo dentro de una tabla concreta
EXTRA = {
    ("clientes", "id_cliente"): ["id", "codigo"],
    ("productos", "id_producto"): ["id", "codigo"],
    ("productos", "costo_unit"): ["costo", "costos", "costo_usd"],
    ("ventas", "id_transaccion"): ["id"],
}


def _norm(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", t).lower()  # camelCase -> camel_case
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def rol_por_nombre(nombre: str):
    """Deduce si un archivo es ventas, clientes o productos por su nombre."""
    n = _norm(nombre)
    for clave, rol in (("venta", "ventas"), ("client", "clientes"), ("product", "productos")):
        if clave in n:
            return rol
    return None


def leer_archivo(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Lee un CSV (separador y codificación autodetectados) o XLSX."""
    try:
        if nombre.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contenido))
        else:
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    df = pd.read_csv(io.BytesIO(contenido), sep=None, engine="python", encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
    except Exception as e:  # archivo corrupto, vacío o de otro formato
        raise ValueError(f"No se pudo leer '{nombre}': archivo vacío, dañado o con formato no válido ({e}).")
    if df.empty:
        raise ValueError(f"El archivo '{nombre}' no contiene filas de datos.")
    return df


def detectar(df: pd.DataFrame, tabla: str) -> dict:
    """Devuelve {campo_canónico: columna_original} para una tabla."""
    cols = {_norm(c): c for c in df.columns}
    mapa, usadas = {}, set()
    for campo in CAMPOS_POR_TABLA[tabla]:
        for alias in ALIASES[campo] + EXTRA.get((tabla, campo), []):
            if alias in cols and cols[alias] not in usadas:
                mapa[campo] = cols[alias]
                usadas.add(cols[alias])
                break
    return mapa


def _clave(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)


def _num(s):
    if s.dtype == object:
        s = s.astype(str).str.replace(r"[^\d,.\-]", "", regex=True)
        ambos = s.str.contains(",") & s.str.contains(r"\.")
        s = s.where(~ambos, s.str.replace(",", "", regex=False))
        solo_coma = s.str.contains(",") & ~s.str.contains(r"\.")
        s = s.where(~solo_coma, s.str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce")


def _fecha(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return s.dt.normalize()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        f = pd.to_datetime(s, errors="coerce")
        if f.isna().mean() > 0.3:
            f = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return f.dt.normalize()


def _preparar(df: pd.DataFrame, tabla: str) -> pd.DataFrame:
    mapa = detectar(df, tabla)
    out = df[list(mapa.values())].rename(columns={v: k for k, v in mapa.items()}).copy()
    for k in ("id_cliente", "id_producto", "id_transaccion"):
        if k in out:
            out[k] = _clave(out[k])
    for k in ("cantidad", "precio", "ventas", "costo", "costo_unit", "latitud", "longitud"):
        if k in out:
            out[k] = _num(out[k])
    if "fecha" in out:
        out["fecha"] = _fecha(out["fecha"])
    for k in ("producto", "categoria", "ciudad", "sucursal", "segmento"):
        if k in out:
            out[k] = out[k].fillna("Sin dato").astype(str).str.strip().replace("", "Sin dato")
    return out


def _unir(df, t, clave, avisos, nombre):
    if clave not in df or clave not in t:
        avisos.append(f"No se encontró la clave '{clave}' en ventas y {nombre}: no se pudo unir esa tabla.")
        return df
    t = t.drop_duplicates(clave)
    nuevas = [c for c in t.columns if c == clave or c not in df.columns]
    return df.merge(t[nuevas], on=clave, how="left")


def construir_dataset(ventas, clientes=None, productos=None):
    """Une las tablas y calcula ventas, costo y utilidad por fila.

    Devuelve (df, avisos, mapeos). Reglas de negocio:
      ventas   = columna de ventas/total, o precio * cantidad si no existe
      costo    = columna de costo total, o costo unitario * cantidad si no existe
      utilidad = ventas - costo
    """
    avisos, mapeos = [], {"ventas": detectar(ventas, "ventas")}
    df = _preparar(ventas, "ventas")
    if clientes is not None:
        mapeos["clientes"] = detectar(clientes, "clientes")
        df = _unir(df, _preparar(clientes, "clientes"), "id_cliente", avisos, "clientes")
    if productos is not None:
        mapeos["productos"] = detectar(productos, "productos")
        df = _unir(df, _preparar(productos, "productos"), "id_producto", avisos, "productos")

    if "fecha" not in df or df["fecha"].notna().sum() == 0:
        raise ValueError("No se encontró una columna de fecha válida en el archivo de ventas.")
    antes = len(df)
    df = df.dropna(subset=["fecha"]).copy()
    if len(df) < antes:
        avisos.append(f"Se descartaron {antes - len(df)} filas sin fecha válida.")

    if "cantidad" not in df:
        df["cantidad"] = 1
        avisos.append("No se encontró 'cantidad': se asumió 1 unidad por fila.")
    df["cantidad"] = df["cantidad"].fillna(0)

    if "ventas" not in df:
        if "precio" in df:
            df["ventas"] = df["precio"] * df["cantidad"]
            avisos.append("No se encontró columna de ventas: se calculó precio × cantidad.")
        else:
            raise ValueError("No se encontró ninguna columna de ventas/total/precio.")
    if "costo" not in df:
        if "costo_unit" in df:
            df["costo"] = df["costo_unit"] * df["cantidad"]
            avisos.append("Costo calculado como costo unitario × cantidad.")
        else:
            df["costo"] = 0.0
            avisos.append("No se encontraron costos: la utilidad será igual a las ventas.")
    df["ventas"], df["costo"] = df["ventas"].fillna(0), df["costo"].fillna(0)

    if "id_transaccion" not in df:
        df["id_transaccion"] = df.index.astype(str)
        avisos.append("No se encontró ID de transacción: cada fila cuenta como una transacción.")
    if "id_cliente" not in df:
        df["id_cliente"] = pd.NA
        avisos.append("No se encontró ID de cliente: el KPI de clientes no es calculable.")
    if "producto" not in df:
        df["producto"] = df["id_producto"] if "id_producto" in df else "Sin dato"
    for c in ("categoria", "ciudad", "sucursal", "segmento"):
        if c not in df:
            df[c] = "Sin dato"
        df[c] = df[c].fillna("Sin dato")
    df["producto"] = df["producto"].fillna("Sin dato")
    df["utilidad"] = df["ventas"] - df["costo"]
    return df.reset_index(drop=True), avisos, mapeos
