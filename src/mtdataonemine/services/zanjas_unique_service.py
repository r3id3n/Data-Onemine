from __future__ import annotations
import os
from datetime import datetime, date, time
from typing import Tuple, Optional

import pandas as pd
from zoneinfo import ZoneInfo

from mtdataonemine.config.env_loader import get_env
from mtdataonemine.repositories.zanjas_unique_repo import fetch_zanjas_unique_raw

_CL_TZ = ZoneInfo("America/Santiago")

def _fmt_sql_dtoffset(dt: datetime) -> str:
    """
    Devuelve un string 'YYYY-mm-dd HH:MM:SS.ffffff ±HH:MM' en hora local CL,
    respetando DST (−03:00/−04:00).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_CL_TZ)
    local = dt.astimezone(_CL_TZ)
    off = local.strftime("%z")  # p.ej. -0300
    off = off[:3] + ":" + off[3:]
    return local.strftime(f"%Y-%m-%d %H:%M:%S.%f {off}")

def build_range_iso(
    start_d: date, start_hhmm: str,
    end_d: date, end_hhmm: str,
) -> Tuple[str, str]:
    h1, m1 = map(int, start_hhmm.split(":"))
    h2, m2 = map(int, end_hhmm.split(":"))
    dt_start = datetime.combine(start_d, time(h1, m1), tzinfo=_CL_TZ)
    dt_end   = datetime.combine(end_d,   time(h2, m2), tzinfo=_CL_TZ)
    return _fmt_sql_dtoffset(dt_start), _fmt_sql_dtoffset(dt_end)

# ===== Config (DB remota del equipo) =====
REMOTE_DB  = get_env("REMOTE_SQL_DATABASE")  or "MTOnemineClient"
REMOTE_USER= get_env("REMOTE_SQL_USER")      or "sa"
REMOTE_PWD = get_env("REMOTE_SQL_PASSWORD")  or ""

def obtener_zanjas_unique(
    ip: str,
    start_date: date, start_hhmm: str,
    end_date: date,   end_hhmm: str,
) -> pd.DataFrame:
    """
    Consulta lecturas en el equipo remoto y devuelve
    un DataFrame DEDUPLICADO por (TagId, MB, Zanja),
    conservando la lectura más reciente (Timestamp).
    Columnas finales: TagId, MB, Zanja, BatteryStatus
    """
    s_iso, e_iso = build_range_iso(start_date, start_hhmm, end_date, end_hhmm)
    raw = fetch_zanjas_unique_raw(
        ip, REMOTE_DB, REMOTE_USER, REMOTE_PWD, s_iso, e_iso,
        timeout=8, retries=2
    )

    if raw is None or raw.empty:
        return pd.DataFrame(columns=["TagId", "MB", "Zanja", "BatteryStatus"])

    df = raw.copy()

    # Aseguramos Timestamp como datetime para ordenar
    if "Timestamp" in df.columns:
        df["__ts__"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df = df.sort_values("__ts__")
    else:
        df["__ts__"] = pd.NaT

    # Dejar una sola fila por (TagId, MB, Zanja) quedándonos con la última (más reciente)
    dedup = df.drop_duplicates(subset=["TagId", "MB", "Zanja"], keep="last")

    # Salida final solicitada
    out = dedup[["TagId", "MB", "Zanja", "BatteryStatus"]].reset_index(drop=True)
    return out

def exportar_zanjas_unique_excel(df: pd.DataFrame, destino: Optional[str] = None) -> str:
    if df is None or df.empty:
        raise ValueError("No hay datos para exportar.")
    if destino is None:
        base = os.path.expanduser("~/Desktop")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(base, f"ZanjasUnique_{ts}.xlsx")
    df.to_excel(destino, index=False)
    return destino
