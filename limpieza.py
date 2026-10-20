"""Limpieza documentada de Online Retail para la serie de venta neta diaria.
Reglas conservadoras: códigos ambiguos se conservan y se reportan para revisión.
"""
import pandas as pd
import numpy as np

# Códigos administrativos inequívocos; revisar descripciones en el notebook.
CODIGOS_ADMIN = {"POST", "DOT", "M", "BANK CHARGES", "AMAZONFEE",
                 "CRUK", "S", "D", "C2", "PADS"}

def preparar(df):
    x = df.copy()
    for c in ("InvoiceNo", "StockCode", "CustomerID"):
        x[c] = x[c].astype("string").str.strip()
    x["Description"] = x["Description"].astype("string")
    x["InvoiceDate"] = pd.to_datetime(x["InvoiceDate"], errors="coerce")
    x["Quantity"] = pd.to_numeric(x["Quantity"], errors="coerce")
    x["UnitPrice"] = pd.to_numeric(x["UnitPrice"], errors="coerce")
    x["importe"] = x["Quantity"] * x["UnitPrice"]
    return x

def limpiar(df, devolver_bitacora=False):
    x = preparar(df)
    registros = []
    def aplicar(nombre, mascara, motivo):
        nonlocal x
        mascara = mascara.fillna(False)
        quitadas = x.loc[mascara]
        registros.append({"orden":len(registros)+1, "regla":nombre,
                          "filas_eliminadas":len(quitadas),
                          "importe_eliminado_GBP":quitadas["importe"].sum(),
                          "justificacion":motivo})
        x = x.loc[~mascara].copy()

    aplicar("Duplicados exactos", x.drop(columns="importe").duplicated(),
            "Evitar contar dos veces una línea idéntica; revisar si hubo repetición legítima.")
    aplicar("Datos esenciales inválidos",
            x["InvoiceDate"].isna() | x["Quantity"].isna() | x["UnitPrice"].isna()
            | x["InvoiceNo"].isna() | x["StockCode"].isna(),
            "No permiten identificar la factura, fecha, artículo o importe.")
    factura = x["InvoiceNo"].str.upper()
    aplicar("Prefijos ajenos a ventas/cancelaciones",
            ~factura.str.match(r"^(?:[0-9]|C[0-9])", na=False),
            "Se conservan facturas numéricas y cancelaciones C seguidas de dígitos.")
    aplicar("Códigos administrativos identificados",
            x["StockCode"].str.upper().isin(CODIGOS_ADMIN),
            "Se excluyen cargos/ajustes que no representan venta de productos.")
    aplicar("Precio no positivo", x["UnitPrice"] <= 0,
            "Líneas sin precio de venta positivo.")
    factura = x["InvoiceNo"].str.upper()
    aplicar("Cantidad negativa sin cancelación",
            (x["Quantity"] < 0) & ~factura.str.match(r"^C[0-9]", na=False),
            "Se separan ajustes de inventario de devoluciones documentadas.")
    aplicar("Cancelación sin cantidad negativa",
            factura.str.match(r"^C[0-9]", na=False) & (x["Quantity"] >= 0),
            "Inconsistencia entre tipo de factura y signo: requiere inspección.")
    aplicar("Cantidad cero", x["Quantity"] == 0, "Sin unidades transaccionadas.")
    x["es_cancelacion"] = x["InvoiceNo"].str.upper().str.match(r"^C[0-9]", na=False)
    x["importe"] = x["Quantity"] * x["UnitPrice"]
    bitacora = pd.DataFrame(registros)
    return (x.reset_index(drop=True), bitacora) if devolver_bitacora else x.reset_index(drop=True)
