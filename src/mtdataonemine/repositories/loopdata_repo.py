from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from mtdataonemine.db.connections import get_engine

def fetch_loopdata(dt_start_iso: str, dt_end_iso: str) -> pd.DataFrame:
    """
    dt_*_iso: strings ISO con offset (ej: '2025-02-26T13:45:00-03:00')
    Devuelve DataFrame con columnas:
      LHD, Operador, Calle, Zanja, CreatedAt, Operacion
    """
    q = text("""
        DECLARE @fechaInicio datetimeoffset(7) = :fecha_inicio;
        DECLARE @fechaFin    datetimeoffset(7) = :fecha_fin;

        SELECT 
            Machine.Name AS LHD,
            (Operator.FirstName + ' ' + Operator.LastName) AS Operador,
            Z.Name AS Calle,
            MTZone.Name AS Zanja,
            CAST(LoopSync.CreatedAt AS smalldatetime) AS CreatedAt,
            LoopOperationType.Name AS Operacion
        FROM LoopSync 
        LEFT JOIN Machine ON LoopSync.MachineId = Machine.MachineId
        LEFT JOIN Operator ON LoopSync.OperatorId = Operator.OperatorId
        RIGHT JOIN MTZone ON MTZone.ZoneId = LoopSync.StartZoneId
        INNER JOIN MTZone Z ON MTZone.ParentZoneId = Z.ZoneId
        LEFT JOIN LoopOperationType ON LoopSync.LoopOperationTypeId = LoopOperationType.LoopOperationTypeId
        WHERE LoopSync.CreatedAt BETWEEN @fechaInicio AND @fechaFin
          AND LoopOperationType.ApplyToCount = 1
        ORDER BY LoopSync.CreatedAt DESC;
    """)
    eng = get_engine()
    with eng.connect() as cx:
        df = pd.read_sql(q, cx, params={"fecha_inicio": dt_start_iso, "fecha_fin": dt_end_iso})
    return df
