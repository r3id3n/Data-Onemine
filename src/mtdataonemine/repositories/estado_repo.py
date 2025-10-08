from __future__ import annotations
from typing import Optional, Tuple
import pandas as pd
import pyodbc

def fetch_estado_between(engine, s_iso: str, e_iso: str) -> pd.DataFrame:
    """
    Lee “Estado” desde la BD local (engine).
    s_iso / e_iso: datetimes con offset formateados (ej: '2025-01-10 08:00:00.0000000 -03:00')
    """
    sql = f"""
    DECLARE @fechaInicio datetimeoffset(7) = '{s_iso}';
    DECLARE @fechaFin    datetimeoffset(7) = '{e_iso}';

    SELECT
        Machine.Name AS LHD,
        Operator.FirstName + ' ' + Operator.LastName AS Operator,
        Status.Name AS Status,
        ISNULL(MTUser.FirstName + ' ' + MTUser.LastName, 'Operador') AS Cambio,
        CAST(StatusLogSync.CreatedAt AS smalldatetime) AS CreatedAt
    FROM [MTOnemineServer].[dbo].[StatusLogSync]
    INNER JOIN Operator ON StatusLogSync.ReporterId = Operator.OperatorId
    INNER JOIN Machine  ON StatusLogSync.MachineId  = Machine.MachineId
    INNER JOIN Status   ON StatusLogSync.StatusId   = Status.StatusId
    LEFT JOIN  MTUser   ON StatusLogSync.UserId     = MTUser.UserId
    WHERE StatusLogSync.CreatedAt BETWEEN @fechaInicio AND @fechaFin
    ORDER BY StatusLogSync.CreatedAt DESC;
    """
    return pd.read_sql_query(sql, engine)


def fetch_machine_status(ip: str, remote_db: str, user: str, pwd: str,
                         dt_start_iso: str, dt_end_iso: str) -> pd.DataFrame:
    """
    Consulta MachineStatusLog en equipo remoto (por IP).
    dt_*_iso en formato 'YYYY-MM-DDTHH:MM:SS' (sin offset, porque el esquema castea strings).
    """
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER=tcp:{ip},1433;"
        f"DATABASE={remote_db};UID={user};PWD={pwd};"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

    sql = f"""
    DECLARE @fechaInicio DATETIME2 = '{dt_start_iso}';
    DECLARE @fechaFin    DATETIME2 = '{dt_end_iso}';

    SELECT *
    FROM MachineStatusLog
    WHERE
        CAST(CAST(MachineStatusLog.timestamp AS VARCHAR(MAX)) AS DATETIME2) >= @fechaInicio
    AND
        CAST(CAST(MachineStatusLog.timestamp AS VARCHAR(MAX)) AS DATETIME2) <= @fechaFin
    ORDER BY
        CAST(CAST(MachineStatusLog.timestamp AS VARCHAR(MAX)) AS DATETIME2) DESC;
    """

    with pyodbc.connect(conn_str) as conn:
        return pd.read_sql_query(sql, conn)
