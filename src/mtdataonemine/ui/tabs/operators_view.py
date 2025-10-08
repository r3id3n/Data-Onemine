from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
import pandas as pd

from mtdataonemine.services.operators_service import (
    obtener_operadores_local,
    filtrar_operadores_df,
    subir_operadores_a_equipo,   # <- nombre correcto del service
)

def build_operators_tab(parent: ctk.CTkFrame, get_selected_ip_cb):
    """
    UI del tab 'Operadores' (independiente de variables globales).
    """
    # ---- Controles ----
    controls = ctk.CTkFrame(parent); controls.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(controls, text="Controles Operador", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(5, 0))

    btn_bar = ctk.CTkFrame(controls); btn_bar.pack(fill="x", padx=10, pady=(6, 0))

    filtro_var = ctk.StringVar(value="")
    operadores_df: pd.DataFrame | None = pd.DataFrame()

    # --- Tabla (se crea antes de usarla) ---
    result = ctk.CTkFrame(parent); result.pack(fill="both", expand=True, padx=10, pady=(10, 10))
    ctk.CTkLabel(result, text="Resultados Operadores", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(5, 0))

    container = ctk.CTkFrame(result); container.pack(fill="both", expand=True, padx=10, pady=10)

    cols = ["OperatorsId", "FirstName", "LastName", "TagId", "SapNumber"]
    tree = ttk.Treeview(container, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center")

    sy = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sy.set)

    tree.pack(side="left", fill="both", expand=True)
    sy.pack(side="right", fill="y")

    # --- Helpers UI ---
    def _mostrar(df: pd.DataFrame):
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            return
        for _, row in df.iterrows():
            tree.insert("", "end", values=[
                row.get("OperatorsId",""),
                row.get("FirstName",""),
                row.get("LastName",""),
                row.get("TagId",""),
                row.get("SapNumber",""),
            ])

    def _cargar():
        nonlocal operadores_df
        try:
            operadores_df = obtener_operadores_local()
            _mostrar(operadores_df)
        except Exception as e:
            messagebox.showerror("Error", f"Error al obtener operadores: {e}")

    def _filtrar():
        if operadores_df is None or operadores_df.empty:
            return
        _mostrar(filtrar_operadores_df(operadores_df, filtro_var.get()))

    def _limpiar():
        filtro_var.set("")
        _filtrar()

    def _subir():
        if operadores_df is None or operadores_df.empty:
            messagebox.showwarning("Advertencia", "Primero debes cargar los operadores.")
            return
        ip = get_selected_ip_cb()
        if not ip:
            messagebox.showerror("Error", "Selecciona un equipo válido (combo superior).")
            return
        try:
            affected = subir_operadores_a_equipo(ip, operadores_df)  # <- nombre correcto
            messagebox.showinfo("Éxito", f"Operadores sincronizados. Filas afectadas: {affected}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al insertar/actualizar en equipo remoto: {e}")

    # --- Botonera ---
    ctk.CTkButton(btn_bar, text="Obtener Operadores", command=_cargar).pack(side="left", padx=6)
    ctk.CTkButton(btn_bar, text="Subir al Equipo", command=_subir).pack(side="left", padx=6)
    ctk.CTkLabel(btn_bar, text="Buscar:").pack(side="left", padx=(12, 4))
    ctk.CTkEntry(btn_bar, textvariable=filtro_var, width=220).pack(side="left", padx=4)
    ctk.CTkButton(btn_bar, text="Filtrar", command=_filtrar).pack(side="left", padx=6)
    ctk.CTkButton(btn_bar, text="Limpiar", command=_limpiar).pack(side="left", padx=6)
