from __future__ import annotations
import os
from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from mtdataonemine.db.connections import get_engine
from mtdataonemine.repositories.calle_repo import (
    fetch_calle_transit_latest_per_point,
    fetch_calles_catalogo,
)

_CL_TZ = ZoneInfo("America/Santiago")

def _to_local_naive_str(d, hhmm: str) -> str:
    # d puede ser datetime.date (DateEntry) o datetime
    if hasattr(d, "year"):
        h, m = map(int, hhmm.split(":"))
        dt = datetime(d.year, d.month, d.day, h, m, 0, tzinfo=_CL_TZ)
    else:
        raise ValueError("Fecha inválida para rango de consulta")
    return dt.astimezone(_CL_TZ).strftime("%Y-%m-%d %H:%M:%S")

def obtener_calle(zone_name: str, start_date, start_hhmm: str, end_date, end_hhmm: str) -> pd.DataFrame:
    s_naive = _to_local_naive_str(start_date, start_hhmm)
    e_naive = _to_local_naive_str(end_date, end_hhmm)

    engine = get_engine()
    df = fetch_calle_transit_latest_per_point(engine, zone_name or "", s_naive, e_naive)

    if df is None or df.empty:
        return df

    if not pd.api.types.is_datetime64_any_dtype(df["TransitDate"]):
        df["TransitDate"] = pd.to_datetime(df["TransitDate"], errors="coerce")

    df["Date"] = df["TransitDate"].dt.date.astype(str)
    df["Time"] = df["TransitDate"].dt.strftime("%H:%M:%S")
    cols = ["Name", "SectorName", "MapPoint", "ZoneName", "Date", "Time"]
    return df.reindex(columns=cols)

def obtener_catalogo_calles() -> pd.DataFrame:
    """
    Devuelve el catálogo completo (Calle/Zanja/TagID/Tipo/Actualizado) desde el servidor.
    """
    engine = get_engine()
    return fetch_calles_catalogo(engine)

def obtener_lista_calles_unicas() -> List[str]:
    """
    Lista única de 'Calle' para el ComboBox.
    """
    engine = get_engine()
    df = fetch_calles_catalogo(engine)
    if df is None or df.empty:
        return []
    # Usa la columna 'Calle' proveniente de a.Name
    return sorted(pd.Series(df["Calle"].dropna().unique()).astype(str).tolist())

def exportar_calle_excel(df: pd.DataFrame, destino: Optional[str] = None) -> str:
    if df is None or df.empty:
        raise ValueError("No hay datos para exportar.")
    if destino is None:
        base = os.path.expanduser("~/Desktop")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(base, f"Calle_{ts}.xlsx")
    df.to_excel(destino, index=False)
    return destino
