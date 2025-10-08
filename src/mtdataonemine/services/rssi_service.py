from __future__ import annotations
import os
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from typing import Tuple, Optional
import pandas as pd

from mtdataonemine.config.env_loader import get_env
from mtdataonemine.repositories.rssi_repo import fetch_rssi_between, fetch_ultimo_lado

# ================= Zona horaria Chile (DST automático) =================
_CL_TZ = ZoneInfo("America/Santiago")


def _fmt_sql_dtoffset(dt: datetime) -> str:
    """Formatea un datetime con tz a string SQL datetimeoffset(7)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_CL_TZ)
    local = dt.astimezone(_CL_TZ)
    off = local.strftime("%z")  # Ejemplo: -0300
    off = off[:3] + ":" + off[3:]  # → -03:00
    return local.strftime(f"%Y-%m-%d %H:%M:%S.%f {off}")


def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    """Convierte 'HH:MM' → (hour, minute)."""
    try:
        h, m = map(int, hhmm.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except Exception:
        raise ValueError(f"Hora inválida: {hhmm!r}")


def _as_localized_dt(d: datetime | date, hhmm: str) -> datetime:
    """Crea un datetime en tz Chile a partir de un date/datetime + hh:mm."""
    h, m = _parse_hhmm(hhmm)
    base_date = d.date() if isinstance(d, datetime) else d
    dt = datetime(base_date.year, base_date.month, base_date.day, h, m)
    return dt.replace(tzinfo=_CL_TZ)


def build_range_iso(
    start_date: datetime | date, start_hhmm: str,
    end_date: datetime | date, end_hhmm: str,
) -> Tuple[str, str]:
    """Devuelve las fechas inicio/fin en formato SQL datetimeoffset."""
    dt_start = _as_localized_dt(start_date, start_hhmm)
    dt_end   = _as_localized_dt(end_date,   end_hhmm)
    return _fmt_sql_dtoffset(dt_start), _fmt_sql_dtoffset(dt_end)


# ================= Configuración conexión DB remota =================
REMOTE_DB = get_env("REMOTE_SQL_DATABASE") or "MTOnemineClient"
REMOTE_USER = get_env("REMOTE_SQL_USER") or "sa"
REMOTE_PWD = get_env("REMOTE_SQL_PASSWORD") or ""


# ================= API de servicio =================
def obtener_rssi(
    ip: str,
    start_date: datetime | date, start_hhmm: str,
    end_date: datetime | date, end_hhmm: str,
) -> pd.DataFrame:
    """Consulta los RSSI entre fechas/horas en el servidor remoto."""
    s_iso, e_iso = build_range_iso(start_date, start_hhmm, end_date, end_hhmm)
    return fetch_rssi_between(ip, REMOTE_DB, REMOTE_USER, REMOTE_PWD, s_iso, e_iso)


def obtener_ultimo_lado(ip: str) -> Optional[str]:
    """Obtiene el último lado seleccionado por un operador en la máquina dada."""
    row = fetch_ultimo_lado(ip, REMOTE_DB, REMOTE_USER, REMOTE_PWD)
    if row is None:
        return None
    return f"{row.get('FirstName','')} {row.get('LastName','')} - Lado: {row.get('Side','')}"


def exportar_rssi_a_excel(df: pd.DataFrame, destino: Optional[str] = None) -> str:
    """Exporta los datos RSSI a un Excel en escritorio (o ruta dada)."""
    if df is None or df.empty:
        raise ValueError("No hay datos RSSI para exportar.")

    if destino is None:
        base = os.path.expanduser("~/Desktop")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = os.path.join(base, f"RSSI_{ts}.xlsx")

    df.to_excel(destino, index=False)
    return destino
