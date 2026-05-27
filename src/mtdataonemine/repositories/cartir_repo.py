from __future__ import annotations
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine
from mtdataonemine.db import get_engine_local


# === SELECTS EN SERVIDOR LOCAL (SQL_DATABASE) ===

def select_cartir_del_dia(engine: Engine) -> pd.DataFrame:
    """TOP 1 Cartir del día (último por CartirId)."""
    q = """
    SELECT TOP (1) CartirId, Name,
           CAST(CreatedAt AS smalldatetime) AS CreatedAt,
           CAST(UpdatedAt AS smalldatetime) AS UpdatedAt
    FROM Cartir
    ORDER BY CartirId DESC
    """
    with engine.connect() as conn:
        return pd.read_sql_query(q, conn)

def select_cartir_por_turno(engine: Engine, cartir_id: int, turno_actual: str) -> pd.DataFrame:
    """
    Detalle de Tasks para un Cartir y turno (A/B).
    """
    q = text("""
        SELECT
            T.TaskId, 
            T.CartirId, 
            S.Name AS Turno, 
            Z3.Name AS Macro, 
            Z2.Name AS Calle, 
            Z.Name AS Zanja,
            T.PailQuantity, 
            T.PailVolume,
            FORMAT(T.CreatedAt, 'yyyy-MM-dd HH:mm:ss') AS CreatedAt
        FROM Task T
        INNER JOIN MTZone Z ON T.SpotId = Z.ZoneId
        INNER JOIN MTZone Z2 ON Z.ParentZoneId = Z2.ZoneId
        INNER JOIN Shift S ON T.ShiftId = S.ShiftId
        INNER JOIN MTZone Z3 ON T.SectorId = Z3.ZoneId
        WHERE T.CartirId = :cartir_id AND S.Name = :turno_actual
    """)
    with engine.connect() as conn:
        return pd.read_sql_query(q, conn, params={"cartir_id": cartir_id, "turno_actual": turno_actual})

def select_resumen_turno(engine: Engine, cartir_id: int, shift_id: int) -> pd.DataFrame:
    q = text("""
        SELECT
            :cartir_id AS CartirId,
            (SELECT Name FROM Shift WHERE ShiftId = :shift_id) AS Shift,
            SUM(PailQuantity) AS Total,
            COUNT(*) AS Ingresos
        FROM Task
        WHERE ShiftId = :shift_id AND CartirId = :cartir_id
        GROUP BY CartirId
    """)
    with engine.connect() as conn:
        return pd.read_sql_query(q, conn, params={"cartir_id": cartir_id, "shift_id": shift_id})


def select_cartir_dia_variable(engine: Engine) -> pd.DataFrame:
    """
    Equivalente a tu obtener_datos() con el ajuste de fechas según hora actual.
    Retorna: CartirsId, Name, CartirDate, CreatedAt, UpdatedAt (formateados).
    """
    hora = datetime.now().hour
    if 0 <= hora < 8:
        q = """
            DECLARE @inputDate datetime = DATEADD(DAY, -1, SYSDATETIMEOFFSET());
            SELECT 
                c.CartirId AS CartirsId, 
                c.Name, 
                FORMAT(c.CartirDate, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS CartirDate,
                FORMAT(c.CreatedAt, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS CreatedAt,
                FORMAT(c.UpdatedAt, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS UpdatedAt
            FROM Cartir c
            WHERE CAST(c.CartirDate AS DATE) = CAST(@inputDate AS DATE);
        """
    else:
        q = """
            DECLARE @inputDate datetime = DATEADD(HOUR, -3, GETDATE());
            SELECT 
                c.CartirId AS CartirsId, 
                c.Name, 
                FORMAT(c.CartirDate, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS CartirDate,
                FORMAT(c.CreatedAt, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS CreatedAt,
                FORMAT(c.UpdatedAt, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS UpdatedAt
            FROM Cartir c
            WHERE CAST(c.CartirDate AS DATE) = CAST(@inputDate AS DATE);
        """
    with engine.connect() as conn:
        return pd.read_sql_query(q, conn)


def select_cartirid_ultimo(engine: Engine) -> int | None:
    q = "SELECT TOP 1 CartirId FROM Cartir ORDER BY CartirDate DESC"
    with engine.connect() as conn:
        df = pd.read_sql_query(q, conn)
    return int(df.iloc[0, 0]) if not df.empty else None


def select_tasks_por_cartir(engine: Engine, cartir_id: int) -> pd.DataFrame:
    q = text("""
        SELECT 
            TaskId, CartirId, ShiftId, SectorId, StreetId, SpotId, 
            NULL AS Placeholder1, PailQuantity, 0 AS Placeholder2, 
            PailVolume, 
            FORMAT(TaskStart, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS TaskStart,
            FORMAT(CreatedAt, 'yyyy-MM-dd HH:mm:ss.fffffff') + ' -03:00' AS CreatedAt,
            NULL AS Placeholder3, NULL AS Placeholder4
        FROM Task
        WHERE CartirId = :cartir_id
    """)
    with engine.connect() as conn:
        return pd.read_sql_query(q, conn, params={"cartir_id": cartir_id})
