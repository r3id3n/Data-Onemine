from __future__ import annotations
import logging
from typing import Optional, Sequence

import pandas as pd
import pyodbc

log = logging.getLogger("mtdataonemine.repositories.zanjas_unique_repo")

_SQL_ZANJAS_RSSI = """
DECLARE @fechaInicio datetimeoffset(7) = ?;
DECLARE @fechaFin    datetimeoffset(7) = ?;

SELECT
    r.TagId                               AS TagId,
    b.Name                                AS MB,
    a.Name                                AS Zanja,
    r.RSSI                                AS RSSI,
    CAST(r.[Timestamp] AS smalldatetime)  AS [Timestamp],
    r.BatteryStatus                       AS BatteryStatus
FROM RawDatas r
INNER JOIN Zones a ON (r.TagId = a.TagId)
RIGHT JOIN  Zones b ON (a.ParentZoneId = b.ZonesId)
WHERE r.CreatedAt >= @fechaInicio
  AND r.CreatedAt <= @fechaFin
ORDER BY r.CreatedAt DESC;
"""

def _conn_string(ip: str, db: str, user: str, pwd: str, timeout: int = 5) -> str:
    # tcp: fuerza TCP y evita resolución DNS rara
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER=tcp:{ip},1433;"
        f"DATABASE={db};UID={user};PWD={pwd};"
        f"TrustServerCertificate=yes;Encrypt=no;"
        f"Connection Timeout={timeout};"
    )

def fetch_zanjas_unique_raw(
    ip: str,
    database: str,
    user: str,
    password: str,
    start_iso: str,
    end_iso: str,
    *,
    timeout: int = 5,
    retries: int = 2,
) -> pd.DataFrame:
    """
    Trae las lecturas RSSI (TagId, MB, Zanja, RSSI, Timestamp, BatteryStatus)
    del equipo remoto entre start_iso y end_iso (ambos en formato con offset,
    ej. 'YYYY-mm-dd HH:MM:SS.ffffff -03:00').

    Retorna un DataFrame (puede estar vacío).
    """
    params: Sequence[object] = (start_iso, end_iso)
    last_err: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            with pyodbc.connect(_conn_string(ip, database, user, password, timeout)) as conn:
                df = pd.read_sql_query(_SQL_ZANJAS_RSSI, conn, params=params)
            return df
        except Exception as e:
            last_err = e
            log.warning("fetch_zanjas_unique_raw intento %s/%s falló: %s",
                        attempt + 1, retries + 1, e)

    # Si llegó aquí, re-lanza la última
    if last_err:
        raise last_err
    return pd.DataFrame()
