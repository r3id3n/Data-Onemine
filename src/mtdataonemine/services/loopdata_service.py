from __future__ import annotations
import pandas as pd
from tkinter import filedialog, messagebox

from mtdataonemine.repositories.loopdata_repo import fetch_loopdata
from mtdataonemine.utils.tz import parse_local_cl, to_sql_datetimeoffset

def load_loopdata(date_start: str, time_start: str, date_end: str, time_end: str) -> pd.DataFrame:
    """
    date_*: 'YYYY-MM-DD' (desde DateEntry)
    time_*: 'HH:MM'     (desde CTkEntry)
    """
    dt_start = parse_local_cl(date_start, time_start)
    dt_end   = parse_local_cl(date_end, time_end)
    df = fetch_loopdata(
        to_sql_datetimeoffset(dt_start),
        to_sql_datetimeoffset(dt_end),
    )
    return df

def filter_df(df: pd.DataFrame, filtros: dict[str,str]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    for col, val in filtros.items():
        if not val or col not in out.columns:
            continue
        s = out[col].astype(str).str.strip().str.lower()
        out = out[s.str.contains(val.strip().lower(), na=False)]
    return out

def export_df_to_excel(df: pd.DataFrame, default_name="LoopData.xlsx") -> None:
    if df is None or df.empty:
        messagebox.showinfo("Exportar", "No hay datos para exportar.")
        return
    path = filedialog.asksaveasfilename(
        title="Guardar resultados",
        defaultextension=".xlsx",
        filetypes=[("Excel (*.xlsx)", "*.xlsx")],
        initialfile=default_name,
    )
    if not path:
        return
    try:
        df.to_excel(path, index=False)
        messagebox.showinfo("Exportar", f"Archivo guardado:\n{path}")
    except Exception as e:
        messagebox.showerror("Exportar", f"No se pudo guardar:\n{e}")
