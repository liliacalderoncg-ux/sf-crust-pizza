"""Datos sintéticos de demostración (solo se usan si no hay archivos reales)."""
import numpy as np
import pandas as pd


def generar(n_ventas: int = 12000, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    ciudades = {"Madrid": (40.4168, -3.7038), "Barcelona": (41.3874, 2.1686),
                "Valencia": (39.4699, -0.3763), "Sevilla": (37.3891, -5.9845)}
    sucursales = {c: [f"{c} Centro", f"{c} Norte"] for c in ciudades}
    prods = [("Margarita", "Pizzas", 11, 3.6), ("Pepperoni", "Pizzas", 13, 4.4), ("Hawaiana", "Pizzas", 12, 4.9),
             ("Cuatro Quesos", "Pizzas", 14, 5.0), ("Vegetariana", "Pizzas", 13, 4.2), ("BBQ Chicken", "Pizzas", 15, 6.0),
             ("Calzone", "Pizzas", 10, 4.8), ("Alitas", "Entradas", 8, 3.9), ("Pan de ajo", "Entradas", 5, 1.2),
             ("Ensalada Caesar", "Entradas", 7, 3.0), ("Gaseosa", "Bebidas", 3, 0.7), ("Limonada", "Bebidas", 3.5, 0.6),
             ("Cerveza artesanal", "Bebidas", 5, 1.9), ("Tiramisú", "Postres", 6, 2.8), ("Brownie", "Postres", 5, 2.4)]
    productos = pd.DataFrame([(f"P{i+1:02d}", *p) for i, p in enumerate(prods)],
                             columns=["ID_Producto", "Producto", "Categoría", "Precio", "Costo_Unitario"])
    n_cli = 500
    cl_ciudad = rng.choice(list(ciudades), n_cli, p=[.4, .3, .2, .1])
    clientes = pd.DataFrame({
        "ID_Cliente": [f"C{i+1:04d}" for i in range(n_cli)], "Nombre": [f"Cliente {i+1}" for i in range(n_cli)],
        "Ciudad": cl_ciudad, "Segmento": rng.choice(["Familias", "Jóvenes", "Corporativo", "Turistas", "VIP"], n_cli, p=[.35, .3, .15, .12, .08]),
        "Latitud": [ciudades[c][0] for c in cl_ciudad], "Longitud": [ciudades[c][1] for c in cl_ciudad]})
    fechas = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 547, n_ventas), unit="D")
    idx_cli = rng.integers(0, n_cli, n_ventas)
    idx_pro = rng.choice(len(prods), n_ventas, p=(w := np.array([14, 14, 9, 8, 7, 8, 4, 8, 7, 4, 8, 5, 6, 4, 4])) / w.sum())
    cant = rng.integers(1, 4, n_ventas)
    ventas = pd.DataFrame({
        "ID_Venta": [f"V{i+1:06d}" for i in range(n_ventas)], "Fecha": fechas,
        "ID_Cliente": clientes["ID_Cliente"].to_numpy()[idx_cli], "ID_Producto": productos["ID_Producto"].to_numpy()[idx_pro],
        "Sucursal": [rng.choice(sucursales[cl_ciudad[i]]) for i in idx_cli], "Cantidad": cant,
        "Total_Venta": np.round(productos["Precio"].to_numpy()[idx_pro] * cant * rng.choice([1, 1, 1, .9], n_ventas), 2)})
    return {"ventas": ventas, "clientes": clientes, "productos": productos}
