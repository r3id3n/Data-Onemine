from __future__ import annotations
import pandas as pd

from mtdataonemine.db.connections import get_engine
from mtdataonemine.repositories.operators_repo import (
    fetch_operadores_local,
    upsert_operadores_remote,
)

__all__ = [
    "obtener_operadores_local",
    "filtrar_operadores_df",
    "subir_operadores_a_equipo",
]

def obtener_operadores_local() -> pd.DataFrame:
    """Retorna operadores desde la BD local."""
    engine = get_engine()
    return fetch_operadores_local(engine)

def filtrar_operadores_df(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    """Filtro contains en todas las columnas (case-insensitive)."""
    if df is None or df.empty:
        return df
    q = (texto or "").strip().lower()
    if not q:
        return df
    mask = df.astype(str).apply(lambda s: s.str.lower().str.contains(q, na=False))
    return df[mask.any(axis=1)]

def subir_operadores_a_equipo(ip: str, operadores_df: pd.DataFrame) -> int:
    """
    Inserta/actualiza operadores en el equipo remoto.
    Devuelve filas procesadas (aprox).
    """
    if operadores_df is None or operadores_df.empty:
        return 0
    # Asegura columnas mínimas
    expected = ["OperatorsId", "FirstName", "LastName", "TagId", "SapNumber"]
    missing = [c for c in expected if c not in operadores_df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")
    return upsert_operadores_remote(ip, operadores_df[expected])
