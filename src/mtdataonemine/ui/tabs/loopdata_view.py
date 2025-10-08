from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk

import pandas as pd
from tkcalendar import DateEntry  # asegúrate de tener tkcalendar instalado

from mtdataonemine.services.loopdata_service import (
    load_loopdata, filter_df, export_df_to_excel
)
from mtdataonemine.utils.tz import current_cl_offset_str

def build_loopdata_tab(parent: ctk.CTkFrame):
    # --- estado ---
    state = {"df": pd.DataFrame()}

    # ---------------- Parámetros ----------------
    params = ctk.CTkFrame(parent); params.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(params, text="Parámetros de Consulta LoopData", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10)

    left = ctk.CTkFrame(params); left.pack(side="left", padx=6)
    right = ctk.CTkFrame(params); right.pack(side="left", padx=6)

    # Fecha/Hora inicio
    row1 = ctk.CTkFrame(left); row1.pack(fill="x")
    ctk.CTkLabel(row1, text="Inicio:").pack(side="left", padx=(0,6))
    fe_ini = DateEntry(row1, width=12); fe_ini.pack(side="left", padx=5)
    t_ini_var = tk.StringVar(value="00:00")
    ctk.CTkEntry(row1, textvariable=t_ini_var, width=70).pack(side="left", padx=5)

    # Fecha/Hora fin
    row2 = ctk.CTkFrame(left); row2.pack(fill="x", pady=(4,0))
    ctk.CTkLabel(row2, text="Fin:").pack(side="left", padx=(0,22))
    fe_fin = DateEntry(row2, width=12); fe_fin.pack(side="left", padx=5)
    t_fin_var = tk.StringVar(value="23:59")
    ctk.CTkEntry(row2, textvariable=t_fin_var, width=70).pack(side="left", padx=5)

    # Offset info (para tranquilidad del operador)
    off_lbl = ctk.CTkLabel(right, text=f"Offset CL actual: {current_cl_offset_str()}")
    off_lbl.pack(anchor="w", padx=10, pady=(6,0))

    # Botones cargar + exportar
    btns = ctk.CTkFrame(params); btns.pack(side="left", padx=10)
    def _cargar():
        date_start = fe_ini.get_date().strftime("%Y-%m-%d")
        date_end   = fe_fin.get_date().strftime("%Y-%m-%d")
        df = load_loopdata(date_start, t_ini_var.get(), date_end, t_fin_var.get())
        state["df"] = df
        _pintar(df)
        _recalc_totales(df)

    ctk.CTkButton(btns, text="Cargar Datos Loop", command=_cargar).pack(side="left", padx=6)
    ctk.CTkButton(btns, text="Exportar a Excel", command=lambda: export_df_to_excel(state["df"]))\
        .pack(side="left", padx=6)

    # ---------------- Filtros ----------------
    filtros = ctk.CTkFrame(parent); filtros.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(filtros, text="Filtros", font=("Arial", 14, "bold"))\
        .grid(row=0, column=0, columnspan=4, sticky="w", padx=10)

    lhd_var = tk.StringVar()
    op_var  = tk.StringVar()
    calle_var = tk.StringVar()
    zanja_var = tk.StringVar()
    total_var = tk.StringVar(value="Total: 0")

    ctk.CTkLabel(filtros, text="LHD:").grid(row=1, column=0, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=lhd_var, width=120).grid(row=1, column=1, padx=5)
    ctk.CTkLabel(filtros, text="Operador:").grid(row=1, column=2, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=op_var, width=150).grid(row=1, column=3, padx=5)

    ctk.CTkLabel(filtros, text="Calle:").grid(row=2, column=0, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=calle_var, width=120).grid(row=2, column=1, padx=5)
    ctk.CTkLabel(filtros, text="Zanja:").grid(row=2, column=2, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=zanja_var, width=150).grid(row=2, column=3, padx=5)

    def _aplicar():
        df = state["df"]
        df2 = filter_df(df, {
            "LHD": lhd_var.get(),
            "Operador": op_var.get(),
            "Calle": calle_var.get(),
            "Zanja": zanja_var.get(),
        })
        _pintar(df2); _recalc_totales(df2)

    def _limpiar():
        lhd_var.set(""); op_var.set(""); calle_var.set(""); zanja_var.set("")
        _pintar(state["df"]); _recalc_totales(state["df"])

    ctk.CTkButton(filtros, text="Aplicar Filtro", command=_aplicar)\
        .grid(row=3, column=0, columnspan=2, pady=10, padx=10)
    ctk.CTkButton(filtros, text="Limpiar Filtros", command=_limpiar)\
        .grid(row=3, column=2, columnspan=2, pady=10, padx=10)

    ctk.CTkLabel(filtros, textvariable=total_var, font=("Arial", 13, "bold"))\
        .grid(row=4, column=0, columnspan=4, sticky="w", padx=10)

    # ---------------- Resultados ----------------
    results = ctk.CTkFrame(parent); results.pack(padx=10, pady=10, fill="both", expand=True)
    ctk.CTkLabel(results, text="Resultados Loop", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(5,0))

    cols = ["LHD","Operador","Calle","Zanja","CreatedAt","Operacion"]
    scroll = tk.Frame(results); scroll.pack(fill="both", expand=True)
    tree_y = ttk.Scrollbar(scroll, orient="vertical")
    tree_x = ttk.Scrollbar(scroll, orient="horizontal")
    tree_y.pack(side="right", fill="y")
    tree_x.pack(side="bottom", fill="x")

    tree = ttk.Treeview(
        scroll, columns=cols, show="headings",
        yscrollcommand=tree_y.set, xscrollcommand=tree_x.set
    )
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=140)
    tree.pack(side="left", fill="both", expand=True)
    tree_y.config(command=tree.yview)
    tree_x.config(command=tree.xview)

    # helpers internos
    def _pintar(df: pd.DataFrame):
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            return
        for _, row in df.iterrows():
            tree.insert("", "end", values=[row.get(c, "") for c in cols])

    def _recalc_totales(df: pd.DataFrame):
        total = int(df["Zanja"].notna().sum()) if (df is not None and "Zanja" in df.columns) else 0
        total_var.set(f"Total: {total}")

    return {
        "tree": tree,
        "state": state,
        "reload": lambda: _cargar()
    }
