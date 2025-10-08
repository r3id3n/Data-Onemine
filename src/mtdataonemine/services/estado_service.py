from __future__ import annotations
import os
from typing import Optional, Tuple
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

from mtdataonemine.db.connections import get_engine
from mtdataonemine.config.env_loader import get_env
from mtdataonemine.repositories.estado_repo import (
    fetch_estado_between,
    fetch_machine_status,
)

# Zona horaria Chile con DST automático (−03/−04 según temporada)
_CL_TZ = ZoneInfo("America/Santiago")

def _fmt_sql_dtoffset(dt: datetime) -> str:
    """Devuelve 'YYYY-mm-dd HH:MM:SS.ffffff -03:00' o -04:00 según DST."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_CL_TZ)
    local = dt.astimezone(_CL_TZ)
    off = local.strftime("%z")      # ej. -0300
    off = off[:3] + ":" + off[3:]   # -> -03:00
    return local.strftime(f"%Y-%m-%d %H:%M:%S.%f {off}")

def build_range_offset(start_date, start_hhmm: str, end_date, end_hhmm: str) -> Tuple[str, str]:
    """Para 'Estado' (lado servidor): retorna strings con offset."""
    h1, m1 = map(int, start_hhmm.split(":"))
    h2, m2 = map(int, end_hhmm.split(":"))
    dt_start = datetime.combine(start_date, time(h1, m1), tzinfo=_CL_TZ)
    dt_end   = datetime.combine(end_date,   time(h2, m2), tzinfo=_CL_TZ)
    return _fmt_sql_dtoffset(dt_start), _fmt_sql_dtoffset(dt_end)

def build_range_naive_iso(start_date, start_hhmm: str, end_date, end_hhmm: str) -> Tuple[str, str]:
    """Para MachineStatus (equipo remoto): 'YYYY-MM-DDTHH:MM:SS' (sin offset)."""
    h1, m1 = map(int, start_hhmm.split(":"))
    h2, m2 = map(int, end_hhmm.split(":"))
    dt_start = datetime.combine(start_date, time(h1, m1))
    dt_end   = datetime.combine(end_date,   time(h2, m2))
    return dt_start.strftime("%Y-%m-%dT%H:%M:%S"), dt_end.strftime("%Y-%m-%dT%H:%M:%S")

# Credenciales remotas por .env (puedes cambiar defaults)
REMOTE_DB = get_env("REMOTE_SQL_DATABASE") or "MTOnemineClient"
REMOTE_USER = get_env("REMOTE_SQL_USER") or "sa"
REMOTE_PWD = get_env("REMOTE_SQL_PASSWORD") or ""

# --------- API ---------
def obtener_estado(start_date, start_hhmm: str, end_date, end_hhmm: str) -> pd.DataFrame:
    s_iso, e_iso = build_range_offset(start_date, start_hhmm, end_date, end_hhmm)
    eng = get_engine()
    return fetch_estado_between(eng, s_iso, e_iso)

def filtrar_estado(df: pd.DataFrame, lhd: str, operador: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    res = df
    if lhd:
        res = res[res["LHD"].astype(str).str.lower().str.contains(lhd.lower())]
    if operador:
        res = res[res["Operator"].astype(str).str.lower().str.contains(operador.lower())]
    return res

def exportar_estado_excel(df: pd.DataFrame, destino: Optional[str] = None) -> str:
    if df is None or df.empty:
        raise ValueError("No hay datos para exportar.")
    if destino is None:
        base = os.path.expanduser("~/Desktop")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(base, f"Estado_{ts}.xlsx")
    df.to_excel(destino, index=False)
    return destino

def obtener_machine_status(ip: str, start_date, start_hhmm: str, end_date, end_hhmm: str) -> pd.DataFrame:
    s_iso, e_iso = build_range_naive_iso(start_date, start_hhmm, end_date, end_hhmm)
    return fetch_machine_status(ip, REMOTE_DB, REMOTE_USER, REMOTE_PWD, s_iso, e_iso)

def exportar_machine_status_excel(df: pd.DataFrame, destino: Optional[str] = None) -> str:
    if df is None or df.empty:
        raise ValueError("No hay datos para exportar.")
    if destino is None:
        base = os.path.expanduser("~/Desktop")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(base, f"MachineStatus_{ts}.xlsx")
    df.to_excel(destino, index=False)
    return destino
