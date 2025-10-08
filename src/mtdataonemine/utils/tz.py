from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo

CL_TZ = ZoneInfo("America/Santiago")

def now_cl() -> datetime:
    """Fecha/hora actual en Chile con tz aware."""
    return datetime.now(CL_TZ)

def parse_local_cl(date_str: str, time_str: str) -> datetime:
    """
    date_str: 'YYYY-MM-DD'
    time_str: 'HH:MM'
    Retorna datetime con zona CL aware.
    """
    y, m, d = map(int, date_str.split("-"))
    hh, mm = map(int, time_str.split(":"))
    return datetime(y, m, d, hh, mm, tzinfo=CL_TZ)

def to_sql_datetimeoffset(dt: datetime) -> str:
    """
    Convierte un datetime aware a string ISO compatible con datetimeoffset de SQL Server.
    Ej: '2025-02-26T13:45:00-03:00'
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CL_TZ)
    # SQL Server entiende ISO 8601; incluimos offset correcto según DST
    return dt.isoformat(timespec="seconds")

def current_cl_offset_str() -> str:
    """Devuelve el offset actual de CL, ej: '-03:00' o '-04:00'."""
    off = now_cl().utcoffset()
    # off es un timedelta (negativo en CL). Normalizamos a ‘±HH:MM’.
    total_minutes = int(off.total_seconds() // 60)
    sign = "-" if total_minutes < 0 else "+"
    total_minutes = abs(total_minutes)
    hh, mm = divmod(total_minutes, 60)
    return f"{sign}{hh:02d}:{mm:02d}"
