from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox

# Necesitas tkcalendar en tus deps
from tkcalendar import DateEntry
import pandas as pd

from mtdataonemine.services.estado_service import (
    obtener_estado, filtrar_estado, exportar_estado_excel,
    obtener_machine_status, exportar_machine_status_excel,
)

def build_estado_tab(parent: ctk.CTkFrame, get_selected_ip_cb):
    """Tab 'Estado' con subpaneles: Estado Select y Machine Status."""
    estado_df: pd.DataFrame | None = pd.DataFrame()
    machine_df: pd.DataFrame | None = pd.DataFrame()

    cont = ctk.CTkFrame(parent); cont.pack(fill="both", expand=True, padx=10, pady=10)

    # ----- Menú lateral -----
    left = ctk.CTkFrame(cont, width=200); left.pack(side="left", fill="y", padx=10, pady=10)
    ctk.CTkLabel(left, text="Menú", font=("Arial", 16, "bold")).pack(pady=5)

    right = ctk.CTkFrame(cont); right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    panel_estado   = ctk.CTkFrame(right)
    panel_machine  = ctk.CTkFrame(right)
    botones: dict[str, ctk.CTkButton] = {}

    def _activar(nombre: str):
        for w in (panel_estado, panel_machine):
            w.pack_forget()
        for b in botones.values():
            b.configure(fg_color="transparent")
        botones[nombre].configure(fg_color=("#3B82F6", "#1E40AF"))
        (panel_estado if nombre == "estado" else panel_machine).pack(fill="both", expand=True)

    def _add_btn(key, text, cb):
        btn = ctk.CTkButton(left, text=text, command=cb); btn.pack(fill="x", pady=5)
        botones[key] = btn

    _add_btn("estado",  "Estado Select",   lambda: _activar("estado"))
    _add_btn("machine", "Máquina Status",  lambda: _activar("machine"))

    # ==================== PANEL: ESTADO ====================
    # Parámetros
    p1 = ctk.CTkFrame(panel_estado); p1.pack(fill="x", padx=10, pady=(10, 6))
    ctk.CTkLabel(p1, text="Consulta de Estado", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)

    fecha_ini = DateEntry(p1, width=12);  fecha_ini.pack(side="left", padx=5)
    hora_ini_var = ctk.StringVar(value="00:00"); ctk.CTkEntry(p1, textvariable=hora_ini_var, width=70).pack(side="left", padx=5)

    fecha_fin = DateEntry(p1, width=12);  fecha_fin.pack(side="left", padx=5)
    hora_fin_var = ctk.StringVar(value="23:59"); ctk.CTkEntry(p1, textvariable=hora_fin_var, width=70).pack(side="left", padx=5)

    def _cargar_estado():
        nonlocal estado_df
        try:
            estado_df = obtener_estado(fecha_ini.get_date(), hora_ini_var.get(), fecha_fin.get_date(), hora_fin_var.get())
            _aplicar_filtro()
        except Exception as e:
            messagebox.showerror("Error", f"Error ejecutando consulta Estado: {e}")

    ctk.CTkButton(p1, text="Obtener Datos", command=_cargar_estado).pack(side="left", padx=10)

    # Filtros
    p2 = ctk.CTkFrame(panel_estado); p2.pack(fill="x", padx=10, pady=(0, 6))
    lhd_var = ctk.StringVar(); op_var = ctk.StringVar()
    ctk.CTkLabel(p2, text="LHD:").pack(side="left", padx=(10, 2))
    ctk.CTkEntry(p2, textvariable=lhd_var, width=120).pack(side="left", padx=5)
    ctk.CTkLabel(p2, text="Operador:").pack(side="left", padx=(10, 2))
    ctk.CTkEntry(p2, textvariable=op_var, width=150).pack(side="left", padx=5)

    def _aplicar_filtro():
        tree.delete(*tree.get_children())
        if estado_df is None or estado_df.empty:
            return
        df = filtrar_estado(estado_df, lhd_var.get(), op_var.get())
        for _, row in df.iterrows():
            tree.insert("", "end", values=[row.get(c,"") for c in cols])

    def _limpiar_filtro():
        lhd_var.set(""); op_var.set(""); _aplicar_filtro()

    ctk.CTkButton(p2, text="Filtrar", command=_aplicar_filtro).pack(side="left", padx=10)
    ctk.CTkButton(p2, text="Limpiar", command=_limpiar_filtro).pack(side="left", padx=6)

    # Resultados + exportar
    p3 = ctk.CTkFrame(panel_estado); p3.pack(fill="both", expand=True, padx=10, pady=(6, 10))
    ctk.CTkLabel(p3, text="Resultados Estado", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)

    cols = ["LHD", "Operator", "Status", "Cambio", "CreatedAt"]
    container = tk.Frame(p3); container.pack(fill="both", expand=True)
    sy = ttk.Scrollbar(container, orient="vertical"); sx = ttk.Scrollbar(container, orient="horizontal")
    sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x")
    tree = ttk.Treeview(container, columns=cols, show="headings", yscrollcommand=sy.set, xscrollcommand=sx.set)
    sy.config(command=tree.yview); sx.config(command=tree.xview)

    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=150)
    tree.pack(side="left", fill="both", expand=True)

    def _exportar_estado():
        try:
            if estado_df is None or estado_df.empty:
                messagebox.showinfo("Info", "No hay datos para exportar.")
                return
            destino = exportar_estado_excel(estado_df)
            messagebox.showinfo("Exportación", f"Archivo creado:\n{destino}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar Estado: {e}")

    ctk.CTkButton(p3, text="Exportar a Excel", command=_exportar_estado).pack(anchor="e", padx=10, pady=6)

    # ==================== PANEL: MACHINE STATUS ====================
    q1 = ctk.CTkFrame(panel_machine); q1.pack(fill="x", padx=10, pady=(10, 6))
    ctk.CTkLabel(q1, text="Consulta de Estado Máquina", font=("Arial", 14, "bold")).pack(anchor="w", padx=10)

    ms_ini = DateEntry(q1, width=12); ms_ini.pack(side="left", padx=5)
    ms_hh_ini = ctk.StringVar(value="00:00"); ctk.CTkEntry(q1, textvariable=ms_hh_ini, width=70).pack(side="left", padx=5)
    ms_fin = DateEntry(q1, width=12); ms_fin.pack(side="left", padx=5)
    ms_hh_fin = ctk.StringVar(value="23:59"); ctk.CTkEntry(q1, textvariable=ms_hh_fin, width=70).pack(side="left", padx=5)

    def _cargar_machine():
        nonlocal machine_df
        ip = get_selected_ip_cb()
        if not ip:
            messagebox.showerror("Error", "Seleccione un equipo válido (combo superior).")
            return
        try:
            machine_df = obtener_machine_status(ip, ms_ini.get_date(), ms_hh_ini.get(), ms_fin.get_date(), ms_hh_fin.get())
            _mostrar_machine()
        except Exception as e:
            messagebox.showerror("Error", f"Error consultando MachineStatusLog: {e}")

    ctk.CTkButton(q1, text="Obtener Datos", command=_cargar_machine).pack(side="left", padx=10)

    q2 = ctk.CTkFrame(panel_machine); q2.pack(fill="both", expand=True, padx=10, pady=(6, 10))
    ctk.CTkLabel(q2, text="Resultados Machine Status", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=5)

    container2 = tk.Frame(q2); container2.pack(fill="both", expand=True)
    sy2 = ttk.Scrollbar(container2, orient="vertical"); sx2 = ttk.Scrollbar(container2, orient="horizontal")
    sy2.pack(side="right", fill="y"); sx2.pack(side="bottom", fill="x")
    tree2 = ttk.Treeview(container2, show="headings", yscrollcommand=sy2.set, xscrollcommand=sx2.set)
    sy2.config(command=tree2.yview); sx2.config(command=tree2.xview)
    tree2.pack(side="left", fill="both", expand=True)

    def _mostrar_machine():
        tree2.delete(*tree2.get_children())
        if machine_df is None or machine_df.empty:
            return
        # Ajustar columnas según DF
        cols2 = list(machine_df.columns)
        tree2["columns"] = cols2
        for c in cols2:
            tree2.heading(c, text=c)
            tree2.column(c, anchor="center", width=150)
        for _, row in machine_df.iterrows():
            tree2.insert("", "end", values=[row.get(c, "") for c in cols2])

    def _exportar_machine():
        try:
            if machine_df is None or machine_df.empty:
                messagebox.showinfo("Info", "No hay datos para exportar.")
                return
            destino = exportar_machine_status_excel(machine_df)
            messagebox.showinfo("Exportación", f"Archivo creado:\n{destino}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar Machine Status: {e}")

    ctk.CTkButton(q2, text="Exportar a Excel", command=_exportar_machine).pack(anchor="e", padx=10, pady=6)

    # Vista inicial
    _activar("estado")
