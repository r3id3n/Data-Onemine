from __future__ import annotations
from mtdataonemine.config.env_loader import load_env_once, debug_dump
load_env_once(verbose=True)

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox, ttk

from mtdataonemine.services.machines_service import obtener_maquinas
from mtdataonemine.services.vnc import conectar_tightvnc
from mtdataonemine.ui.components.ping_panel import PingPanel
from mtdataonemine.ui.tabs.cartir_view import build_cartir_tab
from mtdataonemine.ui.tabs.loopdata_view import build_loopdata_tab
from mtdataonemine.ui.tabs.operators_view import build_operators_tab
from mtdataonemine.ui.tabs.estado_view import build_estado_tab
from mtdataonemine.ui.tabs.tags_view import build_tags_tab 

def build_tab_scaffold(parent: ctk.CTkFrame, title: str, subtitle: str | None = None):
    header = ctk.CTkFrame(parent)
    header.pack(fill="x", padx=10, pady=(10, 6))
    ctk.CTkLabel(header, text=title, font=("Arial", 16, "bold")).pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(header, text=subtitle, font=("Arial", 12)).pack(anchor="w")

    toolbar = ctk.CTkFrame(parent)
    toolbar.pack(fill="x", padx=10, pady=(0, 8))

    body = ctk.CTkFrame(parent)
    body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    footer = ctk.CTkFrame(parent)
    footer.pack(fill="x", padx=10, pady=(0, 10))
    summary = tk.StringVar(value="")
    ctk.CTkLabel(footer, textvariable=summary, anchor="w").pack(anchor="w")
    return toolbar, body, summary


def build_app():
    ctk.set_appearance_mode("dark")
    app = ctk.CTk()
    app.title("MTDataOnemine — MVP")
    app.geometry("1040x700")

    # -------- Barra superior: Combo + VNC --------
    top = ctk.CTkFrame(app)
    top.pack(padx=12, pady=12, fill="x")

    ip_var = tk.StringVar()

    df = obtener_maquinas()
    if df.empty:
        messagebox.showinfo("Sin datos", "No hay máquinas para listar (verifique conexión SQL y .env).")
        values = []
    else:
        values = df[["Name", "IpAddress"]].apply(lambda x: f"{x[0]} - {x[1]}", axis=1).tolist()

    def _ip_from_combo(sel: str) -> str | None:
        if not sel or " - " not in sel:
            return None
        return sel.split(" - ")[1].strip()

    def get_selected_ip():
        return _ip_from_combo(ip_var.get())

    def get_selected_combo_text():
        return ip_var.get()

    combo = ctk.CTkComboBox(top, variable=ip_var, values=values, width=360)
    combo.pack(side="left", padx=(8, 8))

    vnc_btn = ctk.CTkButton(top, text="Conectar VNC", command=lambda: conectar_tightvnc(get_selected_ip()))
    vnc_btn.pack(side="left", padx=8)

    def _update_vnc_btn_state():
        vnc_btn.configure(state=("normal" if get_selected_ip() else "disabled"))

    ping_panel = PingPanel(app, get_selected_ip_cb=get_selected_ip)
    ping_panel.pack(fill="x")

    combo.configure(command=lambda _sel: (ping_panel.on_combo_change(), _update_vnc_btn_state()))

    if values:
        ip_var.set(values[0])
        ping_panel.on_combo_change()
        _update_vnc_btn_state()
    else:
        vnc_btn.configure(state="disabled")

    # -------- Contenedor de pestañas --------
    tabs = ctk.CTkTabview(app)
    tabs.pack(expand=True, fill="both", padx=10, pady=10)

    tab_cartir     = tabs.add("Cartir")
    tab_loop       = tabs.add("LoopData")
    tab_tags       = tabs.add("Tag's") 
    tab_estado     = tabs.add("Estado")
    tab_operadores = tabs.add("Operadores")

    # Cartir
    build_cartir_tab(
        tab_cartir,
        get_selected_ip_cb=get_selected_ip,
        all_equipment_names=[v.split(" - ")[0] for v in values] if values else None,
        get_selected_combo_text_cb=lambda: ip_var.get()
    )

    # LoopData
    build_loopdata_tab(tab_loop)

    # Tag's (incluye RSSI / Zanjas / Calle con menú lateral)
    build_tags_tab(
        tab_tags,
        get_selected_ip_cb=get_selected_ip,
        get_selected_combo_text_cb=get_selected_combo_text  # opcional
    )

    # Estado
    build_estado_tab(tab_estado, get_selected_ip_cb=get_selected_ip)

    # Operadores
    build_operators_tab(tab_operadores, get_selected_ip_cb=get_selected_ip)

    # -------- Cierre limpio --------
    def _on_close():
        try:
            ping_panel.stop()
        finally:
            app.destroy()
    app.protocol("WM_DELETE_WINDOW", _on_close)

    print(debug_dump([
        "SQL_SERVER","SQL_DATABASE","SQL_USER","SQL_PASSWORD","SQL_PORT",
        "REMOTE_SQL_SERVER","REMOTE_SQL_DATABASE","REMOTE_SQL_USER","REMOTE_SQL_PASSWORD","REMOTE_SQL_PORT",
        "VNC_EXE","VNC_PASSWORD"
    ]))

    return app


def main():
    app = build_app()
    app.mainloop()


if __name__ == "__main__":
    main()
