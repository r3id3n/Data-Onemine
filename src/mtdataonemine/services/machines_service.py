from __future__ import annotations
import pandas as pd
import logging
from tkinter import messagebox
from mtdataonemine.repositories.machines_repo import fetch_machines

def _sanitize_ip(ip: str|None) -> str:
    return (ip or "").replace(" ", "")

def obtener_maquinas() -> pd.DataFrame:
    try:
        df = fetch_machines()
        exp = ["MachineId","Name","IpAddress"]
        for c in exp:
            if c not in df.columns: df[c] = pd.NA
        df = df[exp]
        df["IpAddress"] = df["IpAddress"].map(_sanitize_ip)
        df = df.dropna(subset=["IpAddress"])
        df = df[df["IpAddress"] != ""].drop_duplicates(subset=["MachineId","IpAddress"])
        return df.reset_index(drop=True)
    except Exception as e:
        logging.error(f"obtener_maquinas(): {e}")
        messagebox.showerror("Error", f"Error al obtener máquinas: {e}")
        return pd.DataFrame(columns=["MachineId","Name","IpAddress"])
