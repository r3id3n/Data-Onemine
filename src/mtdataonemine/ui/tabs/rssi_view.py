from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import pandas as pd
from datetime import datetime

from mtdataonemine.services.rssi_service import (
    obtener_rssi, obtener_ultimo_lado, exportar_rssi_a_excel
)

def build_rssi_tab(parent: ctk.CTkFrame, get_selected_ip_cb):
    # ---------- Parámetros ----------
    params = ctk.CTkFrame(parent); params.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(params, text="Parámetros de Consulta RSSI", font=("Arial",14,"bold"))\
        .pack(anchor="w", padx=10, pady=(5,0))

    ctk.CTkLabel(params, text="Fecha Inicio:").pack(side="left", padx=(10,5))
    start_date = DateEntry(params, width=12); start_date.pack(side="left", padx=5)
    start_hhmm = ctk.StringVar(value="00:00")
    ctk.CTkEntry(params, textvariable=start_hhmm, width=70).pack(side="left", padx=5)

    ctk.CTkLabel(params, text="Fecha Fin:").pack(side="left", padx=(15,5))
    end_date = DateEntry(params, width=12); end_date.pack(side="left", padx=5)
    end_hhmm = ctk.StringVar(value="23:59")
    ctk.CTkEntry(params, textvariable=end_hhmm, width=70).pack(side="left", padx=5)

    rssi_df: pd.DataFrame | None = None

    # ---------- Filtros ----------
    filtros = ctk.CTkFrame(parent); filtros.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(filtros, text="Filtro por Calle y Zanja", font=("Arial",14,"bold"))\
        .grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5,0))
    f_mb = ctk.StringVar();  f_z = ctk.StringVar()

    ctk.CTkLabel(filtros, text="Calle:").grid(row=1, column=0, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=f_mb, width=150).grid(row=1, column=1, padx=5)

    ctk.CTkLabel(filtros, text="Zanja:").grid(row=1, column=2, sticky="w", padx=(10,5), pady=5)
    ctk.CTkEntry(filtros, textvariable=f_z, width=150).grid(row=1, column=3, padx=5)

    # ---------- Última selección de lado ----------
    lado_box = ctk.CTkFrame(parent); lado_box.pack(padx=10, pady=10, fill="x")
    ctk.CTkLabel(lado_box, text="Última Selección de Lado", font=("Arial",14,"bold"))\
        .pack(anchor="w", padx=10, pady=(5,0))
    lado_var = ctk.StringVar()
    ctk.CTkEntry(lado_box, textvariable=lado_var, state="readonly").pack(fill="x", padx=10, pady=5)

    # ---------- Resultados ----------
    res = ctk.CTkFrame(parent); res.pack(padx=10, pady=10, fill="both", expand=True)
    ctk.CTkLabel(res, text="Resultados RSSI", font=("Arial",14,"bold"))\
        .pack(anchor="w", padx=10, pady=(5,0))

    cols = ["TagId", "Calle", "Zanja", "RSSI", "Timestamp", "BatteryStatus"]
    wrap = tk.Frame(res); wrap.pack(fill="both", expand=True)
    scroll_y = ttk.Scrollbar(wrap, orient="vertical"); scroll_y.pack(side="right", fill="y")
    tree = ttk.Treeview(wrap, columns=cols, show="headings", yscrollcommand=scroll_y.set)
    scroll_y.config(command=tree.yview)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=(100 if c == "RSSI" else 140))
    tree.pack(side="left", fill="both", expand=True)

    # Coloreo por RSSI
    tree.tag_configure("green", foreground="green")
    tree.tag_configure("yellow", foreground="orange")
    tree.tag_configure("red", foreground="red")
    tree.tag_configure("default", foreground="white")

    def _fill_tree(df: pd.DataFrame):
        tree.delete(*tree.get_children())
        if df is None or df.empty:
            return
        for _, row in df.iterrows():
            try:
                rssi = int(float(row.get("RSSI", -999)))
                if 0 >= rssi >= -59:   tag = "green"
                elif -60 >= rssi >= -69: tag = "yellow"
                elif -70 >= rssi >= -100: tag = "red"
                else: tag = "default"
            except Exception:
                tag = "default"
            values = [row.get(c, "") for c in cols]
            tree.insert("", "end", values=values, tags=(tag,))

    # ---------- Acciones ----------
    def _consultar():
        nonlocal rssi_df
        ip = get_selected_ip_cb()
        if not ip:
            messagebox.showerror("Error", "Seleccione una máquina válida.")
            return
        # Lado
        try:
            last = obtener_ultimo_lado(ip)
            lado_var.set(last or "No se encontró información de lado.")
        except Exception as e:
            lado_var.set("No se encontró información de lado.")
        # Datos
        try:
            rssi_df = obtener_rssi(
                ip,
                start_date.get_date(), start_hhmm.get(),
                end_date.get_date(),   end_hhmm.get()
            )
            _fill_tree(rssi_df)
        except Exception as e:
            messagebox.showerror("Error", f"Error en consulta RSSI: {e}")

    def _aplicar_filtro():
        if rssi_df is None or rssi_df.empty:
            messagebox.showinfo("Sin datos","No hay datos para filtrar.")
            return
        df = rssi_df.copy()
        if f_mb.get().strip():
            df = df[df["MB"].astype(str).str.contains(f_mb.get().strip(), case=False, na=False)]
        if f_z.get().strip():
            df = df[df["Zanja"].astype(str).str.contains(f_z.get().strip(), case=False, na=False)]
        _fill_tree(df)

    def _limpiar_filtro():
        f_mb.set(""); f_z.set("")
        _fill_tree(rssi_df if rssi_df is not None else pd.DataFrame())

    def _exportar():
        if rssi_df is None or rssi_df.empty:
            messagebox.showinfo("Sin datos","No hay datos para exportar.")
            return
        try:
            # Dialogo opcional
            path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel","*.xlsx")],
                initialfile=f"RSSI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            if not path:
                return
            exportar_rssi_a_excel(rssi_df, destino=path)
            messagebox.showinfo("Exportación", f"Archivo guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    # Botones
    ctk.CTkButton(params, text="Consultar RSSI", command=_consultar)\
        .pack(side="left", padx=10)
    ctk.CTkButton(filtros, text="Aplicar Filtro", command=_aplicar_filtro)\
        .grid(row=2, column=0, columnspan=2, pady=10, padx=10, sticky="w")
    ctk.CTkButton(filtros, text="Limpiar Filtros", command=_limpiar_filtro)\
        .grid(row=2, column=2, columnspan=2, pady=10, padx=10, sticky="e")
    ctk.CTkButton(parent, text="Exportar a Excel", command=_exportar)\
        .pack(padx=10, pady=(0,10), anchor="w")
