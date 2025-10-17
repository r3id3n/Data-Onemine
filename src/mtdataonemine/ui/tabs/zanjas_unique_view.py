from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import pandas as pd

from mtdataonemine.services.zanjas_unique_service import (
    obtener_zanjas_unique,
    exportar_zanjas_unique_excel,
)

def build_zanjas_unique_tab(parent: ctk.CTkFrame, get_selected_ip_cb):
    """
    Pestaña 'Zanjas (únicas)': muestra TagId, MB, Zanja, BatteryStatus,
    deduplicado por (TagId, MB, Zanja), con filtros por MB y Zanja.
    """

    # --------- Parámetros de consulta ---------
    params = ctk.CTkFrame(parent); params.pack(fill="x", padx=10, pady=(10,6))
    ctk.CTkLabel(params, text="Zanjas (lecturas únicas por TagId/Calle/Zanja)", font=("Arial", 16, "bold"))\
        .pack(anchor="w")

    line = ctk.CTkFrame(params); line.pack(fill="x", padx=6, pady=(6,4))

    # Rango de fechas y horas
    ctk.CTkLabel(line, text="Inicio:").pack(side="left", padx=(6,4))
    d1 = DateEntry(line, width=12); d1.pack(side="left", padx=(0,6))
    h1_var = ctk.StringVar(value="00:00")
    ctk.CTkEntry(line, textvariable=h1_var, width=70).pack(side="left", padx=(0,10))

    ctk.CTkLabel(line, text="Fin:").pack(side="left", padx=(10,4))
    d2 = DateEntry(line, width=12); d2.pack(side="left", padx=(0,6))
    h2_var = ctk.StringVar(value="23:59")
    ctk.CTkEntry(line, textvariable=h2_var, width=70).pack(side="left", padx=(0,10))

    # Botones de acción principal
    btns = ctk.CTkFrame(params); btns.pack(fill="x", padx=6, pady=(0,6))
    ctk.CTkButton(btns, text="Consultar", command=lambda: _consultar()).pack(side="left", padx=6)
    ctk.CTkButton(btns, text="Exportar Excel", command=lambda: _exportar()).pack(side="left", padx=6)

    # --------- Filtros ---------
    filtros = ctk.CTkFrame(parent); filtros.pack(fill="x", padx=10, pady=(0,6))
    ctk.CTkLabel(filtros, text="Filtros", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5,2))

    filtro_mb_var = ctk.StringVar(value="")
    filtro_zanja_var = ctk.StringVar(value="")

    ctk.CTkLabel(filtros, text="Calle:").grid(row=1, column=0, sticky="w", padx=(10,2))
    ctk.CTkEntry(filtros, textvariable=filtro_mb_var, width=120).grid(row=1, column=1, padx=(0,10))

    ctk.CTkLabel(filtros, text="Zanja:").grid(row=1, column=2, sticky="w", padx=(10,2))
    ctk.CTkEntry(filtros, textvariable=filtro_zanja_var, width=120).grid(row=1, column=3, padx=(0,10))

    ctk.CTkButton(filtros, text="Aplicar Filtro", command=lambda: _filtrar()).grid(row=2, column=0, columnspan=2, pady=5, padx=5)
    ctk.CTkButton(filtros, text="Limpiar Filtros", command=lambda: _limpiar_filtros()).grid(row=2, column=2, columnspan=2, pady=5, padx=5)

    # --------- Resultados ---------
    body = ctk.CTkFrame(parent); body.pack(fill="both", expand=True, padx=10, pady=(0,10))

    ctk.CTkLabel(body, text="Detalle (único por TagId, Calle, Zanja)", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=6, pady=(6,4))

    cont = tk.Frame(body); cont.pack(fill="both", expand=True)
    sy = ttk.Scrollbar(cont, orient="vertical"); sy.pack(side="right", fill="y")
    sx = ttk.Scrollbar(cont, orient="horizontal"); sx.pack(side="bottom", fill="x")

    cols = ["TagId", "Calle", "Zanja", "BatteryStatus"]
    tree = ttk.Treeview(cont, columns=cols, show="headings",
                        yscrollcommand=sy.set, xscrollcommand=sx.set)
    sy.config(command=tree.yview); sx.config(command=tree.xview)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=160)
    tree.pack(side="left", fill="both", expand=True)

    # --------- Estado interno ---------
    _df: pd.DataFrame | None = None

    def _fill_tree(df: pd.DataFrame):
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            return
        for _, r in df.iterrows():
            tree.insert("", "end", values=[r.get(c, "") for c in cols])

    def _consultar():
        nonlocal _df
        ip = get_selected_ip_cb()
        if not ip:
            messagebox.showerror("Error", "Selecciona una máquina válida en el combo superior.")
            return
        try:
            _df = obtener_zanjas_unique(
                ip=ip,
                start_date=d1.get_date(), start_hhmm=h1_var.get(),
                end_date=d2.get_date(),   end_hhmm=h2_var.get(),
            )
            if _df is None or _df.empty:
                messagebox.showinfo("Sin datos", "No se encontraron lecturas en el rango seleccionado.")
            _fill_tree(_df)
        except Exception as e:
            messagebox.showerror("Error", f"Error consultando Zanjas únicas: {e}")

    def _filtrar():
        if _df is None or _df.empty:
            messagebox.showinfo("Sin datos", "No hay datos cargados para filtrar.")
            return
        mb = filtro_mb_var.get().strip().lower()
        zanja = filtro_zanja_var.get().strip().lower()
        df_filt = _df.copy()
        if mb:
            df_filt = df_filt[df_filt["Calle"].astype(str).str.lower().str.contains(mb)]
        if zanja:
            df_filt = df_filt[df_filt["Zanja"].astype(str).str.lower().str.contains(zanja)]
        _fill_tree(df_filt)

    def _limpiar_filtros():
        filtro_mb_var.set("")
        filtro_zanja_var.set("")
        _fill_tree(_df)

    def _exportar():
        try:
            if _df is None or _df.empty:
                messagebox.showwarning("Atención", "No hay datos para exportar.")
                return
            ruta = exportar_zanjas_unique_excel(_df)
            messagebox.showinfo("Exportación", f"Archivo generado:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")
