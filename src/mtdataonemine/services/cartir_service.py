from __future__ import annotations
import os, logging
import pandas as pd
import pyodbc
from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Optional, Dict, Any

from mtdataonemine.db.connections import get_engine_local
from mtdataonemine.db.connections import get_engine
from mtdataonemine.repositories.cartir_repo import (
    select_cartir_del_dia, select_cartir_por_turno, select_resumen_turno,
    select_cartir_dia_variable, select_cartirid_ultimo, select_tasks_por_cartir
)

log = logging.getLogger(__name__)

# === Helpers turno ===
def get_turno_actual() -> str:
    hora = datetime.now().hour
    return "A" if 8 <= hora < 20 else "B"

def get_shift_id() -> int:
    return 22 if get_turno_actual() == "A" else 23

# === Conexión remota por IP ===
def _remote_conn_string(ip: str) -> str:
    remote_db = os.getenv("REMOTE_SQL_DATABASE")
    remote_user = os.getenv("REMOTE_SQL_USER")
    remote_pwd  = os.getenv("REMOTE_SQL_PASSWORD")
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=tcp:{ip},1433;"
        f"DATABASE={remote_db};UID={remote_user};PWD={remote_pwd};"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

# === Carga y validación Cartir local → remoto ===
def obtener_datos_cartir_local() -> pd.DataFrame:
    engine = get_engine()
    if engine is None:
        log.error("get_engine() devolvió None")
        return pd.DataFrame()
    return select_cartir_dia_variable(engine)

def validar_cartirs_remoto(ip: str, df: pd.DataFrame, silencioso: bool = True) -> pd.DataFrame:
    """Devuelve solo los Cartirs que NO existen en remoto."""
    if df.empty:
        return pd.DataFrame()

    connstr = _remote_conn_string(ip)
    try:
        with pyodbc.connect(connstr) as cx:
            cur = cx.cursor()
            existentes = set()
            for _, row in df.iterrows():
                cur.execute("SELECT COUNT(*) FROM [dbo].[Cartirs] WHERE CartirsId = ?", (row["CartirsId"],))
                if cur.fetchone()[0] > 0:
                    existentes.add(row["CartirsId"])
            filtrado = df[~df["CartirsId"].isin(existentes)]
            return filtrado
    except Exception as e:
        log.error(f"validar_cartirs_remoto(): {e}")
        return pd.DataFrame()

def insertar_cartirs_remoto(ip: str, df: pd.DataFrame) -> bool:
    df_new = validar_cartirs_remoto(ip, df)
    if df_new.empty:
        log.info("No hay Cartirs nuevos para insertar.")
        return True

    connstr = _remote_conn_string(ip)
    try:
        with pyodbc.connect(connstr) as cx:
            cur = cx.cursor()
            for _, r in df_new.iterrows():
                cur.execute("""
                    INSERT INTO [dbo].[Cartirs] (CartirsId, Name, CartirDate, CreatedAt, UpdatedAt)
                    VALUES (?, ?, ?, ?, ?)
                """, (r["CartirsId"], r["Name"], r["CartirDate"], r["CreatedAt"], r["UpdatedAt"]))
            cx.commit()
        return True
    except Exception as e:
        log.error(f"insertar_cartirs_remoto(): {e}")
        return False

# === Eliminar / insertar Tasks remoto ===
def eliminar_tasks_remoto(ip: str) -> bool:
    connstr = _remote_conn_string(ip)
    hora = datetime.now().hour
    if 0 <= hora < 8:
        q = """
            DECLARE @inputDate datetimeoffset = DATEADD(DAY, -1, SYSDATETIMEOFFSET());
            DELETE FROM Tasks WHERE CAST(TaskStartAt as date) = CAST(@inputDate as date);
        """
    else:
        q = """
            DECLARE @inputDate datetimeoffset = SYSDATETIMEOFFSET();
            DELETE FROM Tasks WHERE CAST(TaskStartAt as date) = CAST(@inputDate as date);
        """
    try:
        with pyodbc.connect(connstr, timeout=10) as cx:
            cur = cx.cursor()
            cur.execute(q)
            cx.commit()
        return True
    except Exception as e:
        log.error(f"eliminar_tasks_remoto(): {e}")
        return False

def insertar_tasks_remoto(ip: str) -> bool:
    engine = get_engine()
    if engine is None:
        return False
    cartir_id = select_cartirid_ultimo(engine)
    if not cartir_id:
        return False

    df = select_tasks_por_cartir(engine, cartir_id)
    if df.empty:
        return True

    df.columns = df.columns.str.lower()
    connstr = _remote_conn_string(ip)
    try:
        with pyodbc.connect(connstr) as cx:
            cur = cx.cursor()
            for _, row in df.iterrows():
                tasks_id = row.get("taskid")
                if tasks_id is None:
                    continue
                cur.execute("SELECT COUNT(*) FROM Tasks WHERE TasksId = ?", (tasks_id,))
                if cur.fetchone()[0] > 0:
                    continue
                cur.execute("""
                    INSERT INTO Tasks (TasksId, CartirId, ShiftId, SectorId, StreetId, SpotId, 
                                       PailQuantity, PailVolume, TaskStartAt, CreatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tasks_id, row.get("cartirid"), row.get("shiftid"),
                    row.get("sectorid"), row.get("streetid"), row.get("spotid"),
                    row.get("pailquantity"), row.get("pailvolume"),
                    row.get("taskstart"), row.get("createdat")
                ))
            cx.commit()
        return True
    except Exception as e:
        log.error(f"insertar_tasks_remoto(): {e}")
        return False

def sincronizar_tasks(ip: str) -> bool:
    if not eliminar_tasks_remoto(ip):
        return False
    return insertar_tasks_remoto(ip)

# === Informe / Resumen en servidor local ===
def cargar_informe_cartir() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Retorna (df_cartir_header, df_resumen_turno, df_detalle).
    """
    engine = get_engine()
    if engine is None:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_cartir = select_cartir_del_dia(engine)
    if df_cartir.empty:
        return df_cartir, pd.DataFrame(), pd.DataFrame()

    cartir_id = int(df_cartir.iloc[0]["CartirId"])
    turno = get_turno_actual()
    shift_id = get_shift_id()

    df_resumen = select_resumen_turno(engine, cartir_id, shift_id)
    df_detalle = select_cartir_por_turno(engine, cartir_id, turno)
    return df_cartir, df_resumen, df_detalle

def get_latest_cartir_info() -> Optional[Dict[str, Any]]:
    """
    Retorna un dict con {CartirId, Name, CreatedAt, UpdatedAt} del último Cartir,
    o None si no existe.
    """
    engine = get_engine_local()
    if engine is None:
        return None

    query = """
        SELECT TOP (1) CartirId, Name,
               CAST(CreatedAt AS smalldatetime) AS CreatedAt,
               CAST(UpdatedAt AS smalldatetime) AS UpdatedAt
        FROM Cartir
        ORDER BY CartirId DESC
    """
    df = pd.read_sql_query(query, engine)
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "CartirId": int(row["CartirId"]),
        "Name": str(row["Name"]),
        "CreatedAt": str(row["CreatedAt"]),
        "UpdatedAt": str(row["UpdatedAt"]),
    }