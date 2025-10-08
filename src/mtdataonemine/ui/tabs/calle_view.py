from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import pandas as pd

from mtdataonemine.services.calle_service import (
    obtener_calle,
    exportar_calle_excel,
    obtener_lista_calles_unicas,
)

def build_calle_tab(parent: ctk.CTkFrame):
    """
    Pestaña 'Calle': consulta vwTransit filtrando por Calle (ZoneName) y rango de fecha/hora.
    ComboBox de calles directo desde el servidor. Exporta a Excel.
    """
    result_df: pd.DataFrame | None = pd.DataFrame()

    # ---------- Parámetros ----------
    frame_params = ctk.CTkFrame(parent)
    frame_params.pack(fill="x", padx=10, pady=(10, 6))
    ctk.CTkLabel(frame_params, text="Consulta de Calle (Último tránsito por punto)", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)

    # ComboBox de Calle (ZoneName)
    calle_var = ctk.StringVar(value="")
    ctk.CTkLabel(frame_params, text="Calle:").pack(side="left", padx=(10, 4))

    # Cargar valores desde servicio (ya usa la columna 'Calle')
    calles_values = []
    try:
        calles_values = obtener_lista_calles_unicas()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar catálogo de calles: {e}")

    combo_calle = ctk.CTkComboBox(frame_params, variable=calle_var, values=calles_values, width=220)
    combo_calle.pack(side="left", padx=(0, 10))

    # Fechas / Horas
    start_date = DateEntry(frame_params, width=12); start_date.pack(side="left", padx=5)
    start_hh = ctk.StringVar(value="00:00"); ctk.CTkEntry(frame_params, textvariable=start_hh, width=70).pack(side="left", padx=5)

    end_date = DateEntry(frame_params, width=12); end_date.pack(side="left", padx=5)
    end_hh = ctk.StringVar(value="23:59"); ctk.CTkEntry(frame_params, textvariable=end_hh, width=70).pack(side="left", padx=5)

    def _consultar():
        nonlocal result_df
        try:
            result_df = obtener_calle(calle_var.get(), start_date.get_date(), start_hh.get(), end_date.get_date(), end_hh.get())
            _mostrar(result_df)
        except Exception as e:
            messagebox.showerror("Error", f"Error ejecutando consulta Calle: {e}")

    ctk.CTkButton(frame_params, text="Consultar", command=_consultar).pack(side="left", padx=10)

    # ---------- Resultados ----------
    frame_result = ctk.CTkFrame(parent)
    frame_result.pack(fill="both", expand=True, padx=10, pady=(6, 10))
    ctk.CTkLabel(frame_result, text="Resultados Calle", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)

    cols = ["Name", "SectorName", "MapPoint", "ZoneName", "Date", "Time"]
    container = tk.Frame(frame_result); container.pack(fill="both", expand=True)
    sy = ttk.Scrollbar(container, orient="vertical"); sx = ttk.Scrollbar(container, orient="horizontal")
    sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x")

    tree = ttk.Treeview(container, columns=cols, show="headings", yscrollcommand=sy.set, xscrollcommand=sx.set)
    sy.config(command=tree.yview); sx.config(command=tree.xview)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=140)
    tree.pack(side="left", fill="both", expand=True)

    def _mostrar(df: pd.DataFrame):
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            return
        for _, row in df.iterrows():
            tree.insert("", "end", values=[row.get(c, "") for c in cols])

    # ---------- Exportar ----------
    def _exportar():
        try:
            if result_df is None or result_df.empty:
                messagebox.showinfo("Info", "No hay datos para exportar.")
                return
            destino = exportar_calle_excel(result_df)
            messagebox.showinfo("Exportación", f"Archivo creado:\n{destino}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    ctk.CTkButton(frame_result, text="Exportar a Excel", command=_exportar).pack(anchor="e", padx=10, pady=6)
