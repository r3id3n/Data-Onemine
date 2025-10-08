from __future__ import annotations
import pandas as pd
from sqlalchemy.engine import Engine

def fetch_calle_transit_latest_per_point(engine: Engine, zone_name: str, start_naive: str, end_naive: str) -> pd.DataFrame:
    sql = f"""
    DECLARE @FechaInicio DATETIME = '{start_naive}';
    DECLARE @FechaFin    DATETIME = '{end_naive}';
    DECLARE @ZoneName    NVARCHAR(128) = '{zone_name.replace("'", "''")}';

    WITH UltimoTransitoPorPunto AS (
        SELECT
            [Name],
            [SectorName],
            [MapPoint],
            [ZoneName],
            [TransitDate],
            ROW_NUMBER() OVER (PARTITION BY [MapPoint] ORDER BY [TransitDate] DESC) AS RowNum
        FROM [MTOnemineServer].[dbo].[vwTransit]
        WHERE
            (@ZoneName = '' OR [ZoneName] = @ZoneName)
            AND [TransitDate] BETWEEN @FechaInicio AND @FechaFin
    )
    SELECT
        [Name],
        [SectorName],
        [MapPoint],
        [ZoneName],
        [TransitDate]
    FROM UltimoTransitoPorPunto
    WHERE RowNum = 1
    ORDER BY TransitDate DESC;
    """
    return pd.read_sql_query(sql, engine)

def fetch_calles_catalogo(engine: Engine) -> pd.DataFrame:
    """
    Devuelve catálogo para el ComboBox de 'Calle'.
    Columnas: Macro, Calle, Tipo
    """
    sql = """
    SELECT
        b.Name AS Macro,
        a.Name AS Calle,
        z.Name AS Tipo
    FROM MTZone a
    RIGHT JOIN ZoneType z ON (a.ZoneTypeId = z.ZoneTypeId)
    RIGHT JOIN MTZone   b ON (a.ParentZoneId = b.ZoneId)
    WHERE z.Name LIKE 'Calle'
    ORDER BY a.Name;
    """
    return pd.read_sql_query(sql, engine)
