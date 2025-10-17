from __future__ import annotations
import logging
import time
from typing import Optional, Sequence, Tuple

import pandas as pd
import pyodbc

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
log = logging.getLogger("mtdataonemine.repositories.rssi_repo")

# -----------------------------------------------------------------------------
# Conexión robusta con timeouts y reintentos
# -----------------------------------------------------------------------------
_DEFAULT_DRIVER = "ODBC Driver 17 for SQL Server"

def _make_conn_str(ip: str, database: str, user: str, password: str, driver: str = _DEFAULT_DRIVER,
                   login_timeout: int = 8) -> str:
    """
    Construye la cadena ODBC para SQL Server (puerto 1433, TCP forzado).
    - login_timeout: segundos máximos para establecer la conexión.
    """
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER=tcp:{ip},1433;"
        f"DATABASE={database};"
        f"UID={user};PWD={password};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
        f"LoginTimeout={login_timeout};"
    )

def _connect(ip: str, database: str, user: str, password: str,
             driver: str = _DEFAULT_DRIVER,
             retries: int = 3,
             login_timeout: int = 8,
             query_timeout: int = 30,
             backoff_seconds: float = 2.0) -> pyodbc.Connection:
    """
    Abre la conexión con reintentos y timeouts.
    - retries: intentos totales antes de fallar
    - login_timeout: timeout de conexión (segundos)
    - query_timeout: timeout por consulta; se aplicará a cada cursor creado
    - backoff_seconds: espera entre intentos
    """
    conn_str = _make_conn_str(ip, database, user, password, driver, login_timeout)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            log.debug(f"[{ip}] Abriendo conexión (intento {attempt}/{retries}) …")
            # El parámetro timeout en pyodbc.connect actúa como query timeout por operación.
            conn = pyodbc.connect(conn_str, timeout=query_timeout)
            log.debug(f"[{ip}] Conexión establecida.")
            return conn
        except Exception as e:
            last_err = e
            log.warning(f"[{ip}] Fallo al conectar (intento {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(backoff_seconds)
    # Si llegó aquí, fallaron todos los intentos
    log.error(f"[{ip}] ❌ Conexión fallida tras {retries} intentos: {last_err}")
    raise last_err

# -----------------------------------------------------------------------------
# Utilidades de ejecución de consultas
# -----------------------------------------------------------------------------
def _execute_to_df(conn: pyodbc.Connection, sql: str, params: Optional[Sequence] = None,
                   query_timeout: Optional[int] = None) -> pd.DataFrame:
    """
    Ejecuta una consulta parametrizada y devuelve DataFrame.
    Ajusta cursor.timeout si se especifica query_timeout.
    """
    cur = conn.cursor()
    try:
        if query_timeout is not None:
            try:
                cur.timeout = int(query_timeout)
            except Exception:
                # Algunos drivers pueden ignorar esta propiedad; igual el connect(timeout=) ya ayuda.
                pass
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame.from_records(rows, columns=cols)
    finally:
        try:
            cur.close()
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Consultas específicas RSSI
# -----------------------------------------------------------------------------
_RSSI_SQL = """
/* RSSI entre rango con zonas y filtro RSSI */
DECLARE @fechaInicio datetimeoffset(7) = ?;
DECLARE @fechaFin    datetimeoffset(7) = ?;

SELECT 
    RawDatas.TagId,
    B.Name AS Calle,
    A.Name AS Zanja,
    RawDatas.RSSI,
    CAST(RawDatas.Timestamp AS smalldatetime) AS [Timestamp],
    RawDatas.BatteryStatus
FROM RawDatas
INNER JOIN Zones A ON RawDatas.TagId = A.TagId
RIGHT JOIN  Zones B ON A.ParentZoneId = B.ZonesId
WHERE RawDatas.CreatedAt >= @fechaInicio
  AND RawDatas.CreatedAt <= @fechaFin
  AND RawDatas.RSSI > ?
ORDER BY RawDatas.CreatedAt DESC;
"""

def fetch_rssi_between(ip: str, database: str, user: str, password: str,
                       fecha_inicio_iso: str, fecha_fin_iso: str,
                       rssi_min: int = -80,
                       *,
                       driver: str = _DEFAULT_DRIVER,
                       retries: int = 3,
                       login_timeout: int = 8,
                       query_timeout: int = 30,
                       backoff_seconds: float = 2.0) -> pd.DataFrame:
    """
    Obtiene RSSI entre [fecha_inicio_iso, fecha_fin_iso] (formato 'YYYY-MM-DD HH:MM:SS.ffffff ±HH:MM').
    Aplica filtro de RSSI > rssi_min.
    """
    conn: Optional[pyodbc.Connection] = None
    try:
        conn = _connect(
            ip, database, user, password,
            driver=driver,
            retries=retries,
            login_timeout=login_timeout,
            query_timeout=query_timeout,
            backoff_seconds=backoff_seconds
        )
        df = _execute_to_df(conn, _RSSI_SQL, params=[fecha_inicio_iso, fecha_fin_iso, rssi_min],
                            query_timeout=query_timeout)
        return df
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

# -----------------------------------------------------------------------------
# Última selección de lado
# -----------------------------------------------------------------------------
_ULTIMO_LADO_SQL = """
SELECT TOP 1
    O.FirstName,
    O.LastName,
    S.Side
FROM Machines M
INNER JOIN Loops L ON (M.MachinesId = L.MachineId)
LEFT JOIN  Operators O ON (O.OperatorsId = L.OperatorId)
RIGHT JOIN SideSelectionLogs S ON (S.OperatorId = O.OperatorsId)
ORDER BY S.CreatedAt DESC;
"""

def fetch_ultimo_lado(ip: str, database: str, user: str, password: str,
                      *,
                      driver: str = _DEFAULT_DRIVER,
                      retries: int = 3,
                      login_timeout: int = 8,
                      query_timeout: int = 30,
                      backoff_seconds: float = 2.0) -> Optional[dict]:
    """
    Devuelve un dict con {FirstName, LastName, Side} o None si no hay datos.
    """
    conn: Optional[pyodbc.Connection] = None
    try:
        conn = _connect(
            ip, database, user, password,
            driver=driver,
            retries=retries,
            login_timeout=login_timeout,
            query_timeout=query_timeout,
            backoff_seconds=backoff_seconds
        )
        df = _execute_to_df(conn, _ULTIMO_LADO_SQL, query_timeout=query_timeout)
        if df is None or df.empty:
            return None
        return df.iloc[0].to_dict()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
