from __future__ import annotations
import logging, os
from urllib.parse import quote_plus
from sqlalchemy import create_engine

# Carga de .env (silenciosa en prod)
from mtdataonemine.config.env_loader import load_env_once, get_env
load_env_once(verbose=False)

LOG_LEVEL = (get_env("LOG_LEVEL") or "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger("mtdataonemine.db")

def _sanitize_host(h: str | None) -> str:
    return (h or "").replace(" ", "")

def _escape_odbc_value(val: str | None) -> str:
    """Escapa ; { } en PWD para cadena ODBC."""
    if not val:
        return ""
    if any(ch in val for ch in (";", "{", "}")):
        return "{" + val.replace("}", "}}") + "}"
    return val

def _build_odbc(server: str, port: int, database: str, user: str, password: str,
                driver: str = "ODBC Driver 17 for SQL Server") -> str:
    server = _sanitize_host(server)
    pwd = _escape_odbc_value(password)
    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={pwd};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
        "LoginTimeout=5;"
    )

def _engine_from_odbc(odbc_str: str):
    # Usamos odbc_connect para evitar problemas de quoting
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_str)}",
        fast_executemany=True,
        pool_pre_ping=True,
        future=True,
    )

# --------- LOCAL (SQL_SERVER / MTOnemineServer) ----------
def get_raw_odbc_local() -> str:
    server   = get_env("SQL_SERVER") or ""
    port     = int(get_env("SQL_PORT") or "1433")
    db       = get_env("SQL_DATABASE") or ""
    user     = get_env("SQL_USER") or ""
    password = get_env("SQL_PASSWORD") or ""
    if not (server and db and user):
        raise RuntimeError("Faltan variables de entorno LOCAL (SQL_*).")
    odbc = _build_odbc(server, port, db, user, password)
    log.debug("Engine LOCAL %s:%s/%s", server, port, db)
    return odbc

def get_engine_local():
    return _engine_from_odbc(get_raw_odbc_local())

# --------- REMOTO (REMOTE_SQL_* / MTOnemineClient) ----------
def get_raw_odbc_remote(ip: str | None = None) -> str:
    server   = ip or (get_env("REMOTE_SQL_SERVER") or "")
    port     = int(get_env("REMOTE_SQL_PORT") or "1433")
    db       = get_env("REMOTE_SQL_DATABASE") or ""
    user     = get_env("REMOTE_SQL_USER") or ""
    password = get_env("REMOTE_SQL_PASSWORD") or ""
    if not (server and db and user):
        raise RuntimeError("Faltan variables de entorno REMOTE (REMOTE_SQL_*).")
    odbc = _build_odbc(server, port, db, user, password)
    log.debug("Engine REMOTE %s:%s/%s", server, port, db)
    return odbc

def get_engine_remote(ip: str | None = None):
    return _engine_from_odbc(get_raw_odbc_remote(ip))

# Alias legacy (si en alguna parte usan get_engine):
def get_engine():
    """Compat: engine LOCAL."""
    return get_engine_local()

__all__ = [
    "get_engine_local",
    "get_engine_remote",
    "get_raw_odbc_local",
    "get_raw_odbc_remote",
    "get_engine",   # compat
]
