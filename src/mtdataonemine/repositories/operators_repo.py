from __future__ import annotations
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import pyodbc

from mtdataonemine.config.env_loader import get_env

# ===== Defaults para la BD remota (puedes sobreescribir vía parámetros) =====
REMOTE_DB_DEFAULT = get_env("REMOTE_SQL_DATABASE") or "MTOnemineClient"
REMOTE_USER_DEFAULT = get_env("REMOTE_SQL_USER") or "sa"
REMOTE_PWD_DEFAULT = get_env("REMOTE_SQL_PASSWORD") or ""

__all__ = [
    "fetch_operadores_local",
    "upsert_operadores_remote",
]

# ---------- LECTURA LOCAL ----------
def fetch_operadores_local(engine) -> pd.DataFrame:
    """
    Lee operadores desde la BD local vía SQLAlchemy engine.
    Devuelve: OperatorsId, FirstName, LastName, TagId, SapNumber
    """
    query = """
        SELECT 
            OperatorId AS OperatorsId,
            FirstName,
            LastName,
            TagId,
            SapNumber
        FROM Operator
    """
    return pd.read_sql_query(query, engine)


# ---------- UPSERT REMOTO ----------
def upsert_operadores_remote(
    ip: str,
    df: pd.DataFrame,
    *,
    remote_db: Optional[str] = None,
    user: Optional[str] = None,
    pwd: Optional[str] = None,
) -> int:
    """
    Inserta/actualiza operadores en el equipo remoto usando MERGE.
    Crea una tabla temporal #tmp_operators, inserta los registros y luego MERGE.

    Columnas esperadas en df:
      - OperatorsId (int)
      - FirstName (str)
      - LastName (str)
      - TagId (int|None)
      - SapNumber (str)

    Retorna: cantidad de filas procesadas (aprox. len(df)).
    """
    if df is None or df.empty:
        return 0

    remote_db = remote_db or REMOTE_DB_DEFAULT
    user = user or REMOTE_USER_DEFAULT
    pwd = pwd or REMOTE_PWD_DEFAULT

    # Normalización vs longitudes típicas en tablas (ajusta si tu schema difiere)
    df = df.copy()
    for col, maxlen in (("FirstName", 50), ("LastName", 50), ("SapNumber", 50)):
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("").str.strip().str[:maxlen]

    if "TagId" in df.columns:
        def _safe_int_or_none(x):
            try:
                return int(x)
            except Exception:
                return None
        df["TagId"] = df["TagId"].apply(_safe_int_or_none)

    # Construir valores para INSERT en #tmp
    rows = [
        (
            int(row.OperatorsId),
            str(row.FirstName) if pd.notna(row.FirstName) else "",
            str(row.LastName) if pd.notna(row.LastName) else "",
            (int(row.TagId) if pd.notna(row.TagId) else None),
            str(row.SapNumber) if pd.notna(row.SapNumber) else "",
        )
        for _, row in df.iterrows()
    ]

    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER=tcp:{ip},1433;"
        f"DATABASE={remote_db};UID={user};PWD={pwd};"
        "TrustServerCertificate=yes;Encrypt=no;"
    )

    create_tmp = """
    IF OBJECT_ID('tempdb..#tmp_operators') IS NOT NULL DROP TABLE #tmp_operators;
    CREATE TABLE #tmp_operators (
        OperatorsId INT NOT NULL,
        FirstName NVARCHAR(50) NOT NULL,
        LastName  NVARCHAR(50) NOT NULL,
        TagId     INT NULL,
        SapNumber NVARCHAR(50) NOT NULL
    );
    """

    insert_tmp = """
    INSERT INTO #tmp_operators (OperatorsId, FirstName, LastName, TagId, SapNumber)
    VALUES (?, ?, ?, ?, ?);
    """

    # Nota: SectorId y CreatedAt fijos/derivados. Ajusta si tu tabla usa otros defaults.
    merge_sql = """
    MERGE INTO Operators AS target
    USING #tmp_operators AS source
        ON target.OperatorsId = source.OperatorsId
    WHEN MATCHED THEN
        UPDATE SET
            target.FirstName = source.FirstName,
            target.LastName  = source.LastName,
            target.TagId     = source.TagId,
            target.SapNumber = source.SapNumber
    WHEN NOT MATCHED THEN
        INSERT (OperatorsId, FirstName, LastName, TagId, SectorId, CreatedAt, SapNumber)
        VALUES (source.OperatorsId, source.FirstName, source.LastName, source.TagId, 1, SYSUTCDATETIME(), source.SapNumber);
    """

    with pyodbc.connect(conn_str) as conn:
        cur = conn.cursor()
        # 1) tabla temporal
        cur.execute(create_tmp)
        # 2) bulk insert
        cur.fast_executemany = True
        cur.executemany(insert_tmp, rows)
        # 3) MERGE
        cur.execute(merge_sql)
        conn.commit()

    # pyodbc.rowcount puede retornar -1 en MERGE; devolvemos len(df) como proxy
    return len(df)
