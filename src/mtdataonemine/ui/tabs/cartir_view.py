from __future__ import annotations
import os
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox
from datetime import datetime
import pandas as pd

from mtdataonemine.services.cartir_service import (
    obtener_datos_cartir_local,
    insertar_cartirs_remoto,
    cargar_informe_cartir,
    sincronizar_tasks,
    get_latest_cartir_info,
)

# ========================= Helpers =========================

def _tree_fill(tree: ttk.Treeview, df: pd.DataFrame | None):
    """Limpia y rellena un Treeview con un DataFrame."""
    tree.delete(*tree.get_children())
    if df is None or getattr(df, "empty", True):
        return
    cols = list(df.columns)
    tree["columns"] = cols
    tree["show"] = "headings"
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, anchor="center", width=max(100, int(900 / max(1, len(cols)))))
    for _, row in df.iterrows():
        tree.insert("", "end", values=[row.get(c, "") for c in cols])


def _mostrar_listado_actual(
    label_fecha: ctk.CTkLabel,
    txt_actualizados: tk.Text,
    txt_faltantes: tk.Text | None,
    all_equipment_names: list[str] | None,
):
    """
    Lee listado_actual.txt y actualiza los widgets.
    Si se entrega all_equipment_names, calcula faltantes.
    """
    path_log = r"C:\Users\admalex\Desktop\app\listado_actual.txt"

    if not os.path.exists(path_log):
        # limpiar vistas
        label_fecha.configure(text="Ejecutado: -")
        txt_actualizados.configure(state="normal")
        txt_actualizados.delete("1.0", tk.END)
        txt_actualizados.configure(state="disabled")
        if txt_faltantes is not None:
            txt_faltantes.configure(state="normal")
            txt_faltantes.delete("1.0", tk.END)
            txt_faltantes.configure(state="disabled")
        return

    with open(path_log, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    if len(lineas) < 2:
        label_fecha.configure(text="Ejecutado: -")
        return

    fecha = lineas[0].strip()
    equipos_str = lineas[1].strip()
    equipos_report = [x for x in equipos_str.split("-") if x]

    label_fecha.configure(text=fecha)

    txt_actualizados.configure(state="normal")
    txt_actualizados.delete("1.0", tk.END)
    txt_actualizados.insert(tk.END, "-".join(equipos_report))
    txt_actualizados.configure(state="disabled")

    # Faltantes (solo si se entregó la lista completa)
    if txt_faltantes is not None and all_equipment_names:
        reported_set = set(equipos_report)
        faltantes = [eq for eq in all_equipment_names if eq not in reported_set]
        txt_faltantes.configure(state="normal")
        txt_faltantes.delete("1.0", tk.END)
        txt_faltantes.insert(tk.END, "-".join(faltantes))
        txt_faltantes.configure(state="disabled")

def _append_equipo_a_listado_y_refrescar(
    equipo_nombre: str,
    label_fecha: ctk.CTkLabel,
    txt_actualizados: tk.Text,
    txt_faltantes: tk.Text | None,
    all_equipment_names: list[str] | None,
):
    """
    Inserta (si no existe) el nombre en listado_actual.txt y refresca ambos paneles.
    """
    path = r"C:\Users\admalex\Desktop\app\listado_actual.txt"
    existentes: set[str] = set()

    # Lee existentes
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        if len(lineas) >= 2:
            existentes = set([x for x in lineas[1].strip().split("-") if x])

    # Agrega si no estaba
    if equipo_nombre:
        existentes.add(equipo_nombre)

    # Escribe archivo
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-".join(sorted(existentes)))

    # Refresca UI (Actualizados y Faltantes globales)
    _mostrar_listado_actual(label_fecha, txt_actualizados, txt_faltantes, all_equipment_names)


# ========================= Vista principal =========================

def build_cartir_tab(
    parent: ctk.CTkFrame,
    get_selected_ip_cb,
    all_equipment_names: list[str] | None = None,
    get_selected_combo_text_cb = None,
):
    """
    parent: Frame del tab "Cartir"
    get_selected_ip_cb: callback que retorna la IP seleccionada (o None)
    all_equipment_names: lista opcional con todos los equipos (ej. ["LE001",...]) para calcular faltantes
    """

    # ----- Toolbar superior -----
    toolbar = ctk.CTkFrame(parent)
    toolbar.pack(fill="x", padx=10, pady=(6, 2))

    # ----- Layout: izquierda (menú) + derecha (panel dinámico) -----
    container = ctk.CTkFrame(parent)
    container.pack(fill="both", expand=True)
    left = ctk.CTkFrame(container, width=200)
    left.pack(side="left", fill="y", padx=10, pady=10)
    right = ctk.CTkFrame(container)
    right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(left, text="Menú", font=("Arial", 16, "bold")).pack(pady=5)

    # Paneles
    panel_servidor = ctk.CTkFrame(right)
    panel_equipos  = ctk.CTkFrame(right)
    panel_informe  = ctk.CTkFrame(right)

    # ----- conmutador de paneles -----
    botones: dict[str, ctk.CTkButton] = {}

    def _activar(nombre: str):
        for w in (panel_servidor, panel_equipos, panel_informe):
            w.pack_forget()
        for _, b in botones.items():
            b.configure(fg_color="transparent")

        # Orden: informe → equipos → servidor
        if nombre == "informe":
            panel_informe.pack(fill="both", expand=True)
        elif nombre == "equipos":
            panel_equipos.pack(fill="both", expand=True)
        else:
            panel_servidor.pack(fill="both", expand=True)

        botones[nombre].configure(fg_color=("#3B82F6", "#1E40AF"))

    def _add_btn(key: str, text: str, target: str):
        btn = ctk.CTkButton(left, text=text, command=lambda: _activar(target))
        btn.pack(fill="x", pady=5)
        botones[key] = btn

    _add_btn("informe",  "Datos Informe",  "informe")
    _add_btn("equipos",  "Datos Equipos",  "equipos")
    _add_btn("servidor", "Datos Servidor", "servidor")

    # ================== PANEL: SERVIDOR ==================
    ctk.CTkLabel(panel_servidor, text="Servidor", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(10, 6))

    turno_lbl = ctk.CTkLabel(panel_servidor, text="", font=("Arial", 13, "bold"))
    turno_lbl.pack(anchor="w", padx=10, pady=(0, 6))

    # Cabecera Cartir (CartirId / CreatedAt / UpdatedAt)
    cartir_header = ctk.CTkFrame(panel_servidor)
    cartir_header.pack(fill="x", padx=10, pady=(0, 10))
    cartir_id_var      = tk.StringVar(value="-")
    cartir_created_var = tk.StringVar(value="-")
    cartir_updated_var = tk.StringVar(value="-")

    for col in (1, 3, 5):
        cartir_header.grid_columnconfigure(col, weight=1)

    ctk.CTkLabel(cartir_header, text="CartirId:",  font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0,6))
    ctk.CTkLabel(cartir_header, textvariable=cartir_id_var).grid(row=0, column=1, sticky="we", padx=(0,20))
    ctk.CTkLabel(cartir_header, text="CreatedAt:", font=("Arial", 12, "bold")).grid(row=0, column=2, sticky="w", padx=(0,6))
    ctk.CTkLabel(cartir_header, textvariable=cartir_created_var).grid(row=0, column=3, sticky="we", padx=(0,20))
    ctk.CTkLabel(cartir_header, text="UpdatedAt:", font=("Arial", 12, "bold")).grid(row=0, column=4, sticky="w", padx=(0,6))
    ctk.CTkLabel(cartir_header, textvariable=cartir_updated_var).grid(row=0, column=5, sticky="we")

    # Resumen Macro/Calle (texto)
    resumen_text = tk.Text(
        panel_servidor,
        wrap="word",
        bg="#1a1a1a",
        fg="white",
        borderwidth=0,
        highlightthickness=0,
    )
    resumen_text.pack(fill="x", padx=10, pady=(0, 10))

    # ================== PANEL: EQUIPOS ==================
    ctk.CTkLabel(panel_equipos, text="Sincronización de Datos", font=("Arial", 14, "bold"))\
        .pack(anchor="w", padx=10, pady=(10, 6))

    frame_sync = ctk.CTkFrame(panel_equipos)
    frame_sync.pack(fill="x", padx=10, pady=(0, 10))

    def _insertar_y_sincronizar():
        """Botón único: Insertar Cartir + Sincronizar Tasks + actualizar listado_actual.txt (por nombre de equipo)."""
        ip = get_selected_ip_cb()
        if not ip:
            messagebox.showerror("Error", "Seleccione una máquina válida (combobox superior).")
            return

        # Tomar nombre limpio del equipo desde el combo si está disponible
        equipo_nombre = None
        try:
            # Si tu main.py ya pasa solo el nombre: "LE001"
            if 'get_selected_combo_text_cb' in locals() and callable(get_selected_combo_text_cb):
                raw = get_selected_combo_text_cb() or ""
                equipo_nombre = raw.split(" - ")[0].strip() if " - " in raw else raw.strip()
        except Exception:
            equipo_nombre = None  # no bloqueamos la sync por esto

        try:
            # 1) Insertar Cartir (si hay datos)
            df_cartir_local = obtener_datos_cartir_local()
            if df_cartir_local is None or df_cartir_local.empty:
                messagebox.showwarning("Advertencia", "No hay datos de Cartir para insertar.")
            else:
                ok_c = insertar_cartirs_remoto(ip, df_cartir_local)
                if not ok_c:
                    messagebox.showerror("Cartir", "Error insertando Cartir en remoto.")
                    return  # si falla Cartir, no seguimos

            # 2) Sincronizar Tasks (eliminar + insertar)
            ok_t = sincronizar_tasks(ip)
            if not ok_t:
                messagebox.showerror("Tasks", "Error durante la sincronización de Tasks.")
                return

            # 3) Si todo salió bien: escribir/actualizar listado_actual.txt con el NOMBRE del equipo
            if equipo_nombre:
                import os
                path = r"C:\Users\admalex\Desktop\app\listado_actual.txt"

                existentes: set[str] = set()
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        lineas = f.readlines()
                    if len(lineas) >= 2:
                        existentes = set([x for x in lineas[1].strip().split("-") if x])

                existentes.add(equipo_nombre)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-".join(sorted(existentes)))

            # 4) Refrescar panel de listados (Actualizados + Faltantes)
            _mostrar_listado_actual(
                label_actualizados_fecha,
                text_equipos_actualizados,
                text_equipos_faltantes,  # usa all_equipment_names para calcular faltantes
                all_equipment_names,
            )

            messagebox.showinfo("OK", "Sincronización completa (Cartir + Tasks).")

        except Exception as e:
            messagebox.showerror("Error", f"Error en la sincronización: {e}")


    ctk.CTkButton(
        frame_sync, text="Sincronizar (Cartir + Tasks)", command=_insertar_y_sincronizar
    ).pack(side="left", padx=10, pady=10)


    def _actualizar_equipos_externo():
        """Ejecuta EXE externo y mergea equipos_completados.txt → listado_actual.txt."""
        import subprocess
        import logging
        import os

        try:
            exe_path = r"C:\Users\admalex\Desktop\app\CARTIR_NightShift.exe"
            completados_path = r"C:\Users\admalex\Desktop\app\equipos_completados.txt"
            listado_actual_path = r"C:\Users\admalex\Desktop\app\listado_actual.txt"

            subprocess.run([exe_path], check=True)

            # Merge
            nuevos = set()
            if os.path.exists(completados_path):
                with open(completados_path, "r", encoding="utf-8") as f:
                    lineas = [l.strip() for l in f.readlines() if l.strip()]
                if lineas:
                    nuevos = set(lineas[-1].split("-"))

            existentes = set()
            if os.path.exists(listado_actual_path):
                with open(listado_actual_path, "r", encoding="utf-8") as f:
                    lineas = f.readlines()
                if len(lineas) >= 2:
                    existentes = set([x for x in lineas[1].strip().split("-") if x])

            union = sorted(existentes.union(nuevos))
            with open(listado_actual_path, "w", encoding="utf-8") as f:
                f.write(f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-".join(union))

            _mostrar_listado_actual(
                label_actualizados_fecha,
                text_equipos_actualizados,
                text_equipos_faltantes,
                all_equipment_names,
            )
            messagebox.showinfo("Éxito", "Equipos actualizados correctamente.")

        except Exception as e:
            logging.error(f"Error al actualizar equipos: {e}")
            messagebox.showerror("Error", f"Ocurrió un error al actualizar equipos: {e}")


    ctk.CTkButton(
        frame_sync, text="Actualizar Equipos (EXE)", command=_actualizar_equipos_externo
    ).pack(side="left", padx=10, pady=10)

    # --- Equipos Actualizados ---
    frame_equipos_actualizados = ctk.CTkFrame(panel_equipos)
    frame_equipos_actualizados.pack(pady=10, padx=10, fill="both", expand=False)

    ctk.CTkLabel(
        frame_equipos_actualizados,
        text="Equipos Actualizados",
        font=("Arial", 14, "bold"),
    ).pack(anchor="w", padx=10, pady=(5, 0))

    label_actualizados_fecha = ctk.CTkLabel(
        frame_equipos_actualizados, text="Ejecutado: -"
    )
    label_actualizados_fecha.pack(anchor="w", padx=10, pady=(0, 5))

    text_equipos_actualizados = tk.Text(
        frame_equipos_actualizados, height=5, wrap="word"
    )
    text_equipos_actualizados.pack(pady=5, fill="both", expand=True)
    text_equipos_actualizados.configure(state="disabled")

    def _copiar_listado_actualizado():
        contenido = text_equipos_actualizados.get("1.0", tk.END).strip()
        if not contenido:
            return
        top = parent.winfo_toplevel()
        top.clipboard_clear()
        top.clipboard_append(contenido)
        top.update()
        messagebox.showinfo(
            "Copiado", "Listado de equipos actualizado copiado al portapapeles."
        )

    ctk.CTkButton(
        frame_equipos_actualizados,
        text="Copiar al portapapeles",
        command=_copiar_listado_actualizado,
    ).pack(pady=5)

    # --- Equipos Faltantes (opcional) ---
    frame_equipos_faltantes = ctk.CTkFrame(panel_equipos)
    frame_equipos_faltantes.pack(pady=10, padx=10, fill="both", expand=False)

    ctk.CTkLabel(
        frame_equipos_faltantes,
        text="Equipos Faltantes",
        font=("Arial", 14, "bold"),
    ).pack(anchor="w", padx=10, pady=(5, 0))

    text_equipos_faltantes = tk.Text(
        frame_equipos_faltantes, height=5, fg="red", wrap="word"
    )
    text_equipos_faltantes.pack(pady=5, fill="both", expand=True)
    text_equipos_faltantes.configure(state="disabled")

    # Primer refresco desde archivo (si existe)
    _mostrar_listado_actual(
        label_actualizados_fecha,
        text_equipos_actualizados,
        text_equipos_faltantes,
        all_equipment_names,
    )

    # ================== PANEL: INFORME ==================
    ctk.CTkLabel(panel_informe, text="Informe Cartir del Día", font=("Arial", 16, "bold"))\
        .pack(pady=10)

    frame_inf = ctk.CTkFrame(panel_informe)
    frame_inf.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # --- Cartir del día ---
    ctk.CTkLabel(frame_inf, text="Cartir del día", font=("Arial", 13, "bold")).pack(anchor="w")
    tree1 = ttk.Treeview(frame_inf, show="headings", height=2)
    tree1.pack(fill="x", pady=(2, 8))

    # --- Resumen por turno ---
    ctk.CTkLabel(frame_inf, text="Resumen por turno", font=("Arial", 13, "bold")).pack(anchor="w")
    tree2 = ttk.Treeview(frame_inf, show="headings", height=3)
    tree2.pack(fill="x", pady=(2, 8))

    # --- Total por macro (tabla) ---
    ctk.CTkLabel(frame_inf, text="Total por macro", font=("Arial", 13, "bold")).pack(anchor="w", pady=(4, 0))
    tree_macro = ttk.Treeview(
        frame_inf, columns=["Macro", "Total PailQuantity"], show="headings", height=4
    )
    for col in ["Macro", "Total PailQuantity"]:
        tree_macro.heading(col, text=col)
        tree_macro.column(col, anchor="center", width=160)
    tree_macro.pack(fill="x", pady=(2, 6))

    # --------- Detalle de Tasks (filtros) solo en INFORME ---------
    ctk.CTkLabel(frame_inf, text="Detalle de Tasks", font=("Arial", 13, "bold")).pack(anchor="w", pady=(6, 2))

    filtros_det = ctk.CTkFrame(frame_inf)
    filtros_det.pack(fill="x", pady=(0, 4))

    det_calle_var = tk.StringVar()
    det_zanja_var = tk.StringVar()

    ctk.CTkLabel(filtros_det, text="Calle:").pack(side="left", padx=(2, 2))
    ctk.CTkEntry(filtros_det, textvariable=det_calle_var, width=140).pack(side="left", padx=(0, 8))
    ctk.CTkLabel(filtros_det, text="Zanja:").pack(side="left", padx=(2, 2))
    ctk.CTkEntry(filtros_det, textvariable=det_zanja_var, width=140).pack(side="left", padx=(0, 8))

    # Solo estas columnas:
    det_cols = ["Turno", "Macro", "Calle", "Zanja", "PailQuantity", "PailVolume"]

    container_det = ctk.CTkFrame(frame_inf)
    container_det.pack(fill="both", expand=True, pady=(2, 6))

    tree_det = ttk.Treeview(container_det, columns=det_cols, show="headings")
    for c in det_cols:
        tree_det.heading(c, text=c)
        tree_det.column(c, anchor="center", width=130 if c != "Calle" else 180)
    sy_det = ttk.Scrollbar(container_det, orient="vertical", command=tree_det.yview)
    sx_det = ttk.Scrollbar(container_det, orient="horizontal", command=tree_det.xview)
    tree_det.configure(yscrollcommand=sy_det.set, xscrollcommand=sx_det.set)
    tree_det.pack(side="left", fill="both", expand=True)
    sy_det.pack(side="right", fill="y")
    sx_det.pack(side="bottom", fill="x")

    det_cache: pd.DataFrame | None = None  # cache del detalle para filtros

    def _pintar_detalle(df: pd.DataFrame | None):
        if df is None or df.empty:
            _tree_fill(tree_det, pd.DataFrame(columns=det_cols))
            return
        # Garantizar columnas necesarias y orden correcto
        view_df = pd.DataFrame(columns=det_cols)
        for c in det_cols:
            if c in df.columns:
                view_df[c] = df[c]
            else:
                view_df[c] = ""
        _tree_fill(tree_det, view_df)

    def _filtrar_detalle():
        base = det_cache if det_cache is not None else pd.DataFrame()
        if base.empty:
            _pintar_detalle(base)
            return
        df = base.copy()
        cval = det_calle_var.get().strip().lower()
        zval = det_zanja_var.get().strip().lower()
        if cval and "Calle" in df.columns:
            df = df[df["Calle"].astype(str).str.lower().str.contains(cval, na=False)]
        if zval and "Zanja" in df.columns:
            df = df[df["Zanja"].astype(str).str.lower().str.contains(zval, na=False)]
        _pintar_detalle(df)

    def _limpiar_filtros_detalle():
        det_calle_var.set("")
        det_zanja_var.set("")
        _filtrar_detalle()

    ctk.CTkButton(filtros_det, text="Filtrar", command=_filtrar_detalle).pack(side="left", padx=6)
    ctk.CTkButton(filtros_det, text="Limpiar", command=_limpiar_filtros_detalle).pack(side="left", padx=2)

    # ---------- Lógica de carga ----------
    def _refresh_header_only():
        """Refresca turno + CartirId/CreatedAt/UpdatedAt."""
        turno_lbl.configure(text=f"Turno actual: {'A' if 8 <= datetime.now().hour < 20 else 'B'}")
        df_info = get_latest_cartir_info()
        if isinstance(df_info, dict):
            df_info = pd.DataFrame([df_info])
        if df_info is None or getattr(df_info, "empty", True):
            cartir_id_var.set("-"); cartir_created_var.set("-"); cartir_updated_var.set("-")
            return
        r = df_info.iloc[0]
        cartir_id_var.set(str(r.get("CartirId", "-")))
        cartir_created_var.set(str(r.get("CreatedAt", "-")))
        cartir_updated_var.set(str(r.get("UpdatedAt", "-")))

    def _generar_informe(df_detalle: pd.DataFrame | None):
        """Llena Cartir del día / Resumen por turno / Total por macro (tabla)."""
        nonlocal det_cache
        df_cartir, df_resumen, df_detalle_srv = cargar_informe_cartir()

        # Cabeceras tablas superiores
        if df_cartir is None or df_cartir.empty:
            for t in (tree1, tree2, tree_macro):
                t.delete(*t.get_children())
        else:
            _tree_fill(tree1, df_cartir)
            _tree_fill(tree2, df_resumen)

        # Totales por Macro
        det_total = df_detalle if df_detalle is not None else df_detalle_srv
        try:
            df_macro = det_total.groupby("Macro")["PailQuantity"].sum().reset_index()
            df_macro = df_macro.rename(columns={"PailQuantity": "Total PailQuantity"})
        except Exception:
            df_macro = pd.DataFrame(columns=["Macro", "Total PailQuantity"])

        tree_macro.delete(*tree_macro.get_children())
        for _, row in df_macro.iterrows():
            tree_macro.insert("", "end", values=[row["Macro"], int(row["Total PailQuantity"])])

        # ---- cachear y pintar Detalle con columnas solicitadas ----
        det_cache = det_total if det_total is not None else pd.DataFrame()
        _pintar_detalle(det_cache)

    def _cargar_servidor():
        """Rellena resumen Macro/Calle + refresca informe."""
        resumen_text.configure(state="normal")
        resumen_text.delete("1.0", tk.END)

        df_cartir, _df_res, df_detalle = cargar_informe_cartir()
        if df_cartir is None or df_cartir.empty:
            messagebox.showinfo("Info", "No se encontró Cartir.")
            resumen_text.configure(state="disabled")
            # limpiar informe
            for t in (tree1, tree2, tree_macro):
                t.delete(*t.get_children())
            # vaciar detalle
            _pintar_detalle(pd.DataFrame(columns=det_cols))
            return

        turno_lbl.configure(text=f"Turno actual: {'A' if 8 <= datetime.now().hour < 20 else 'B'}")

        # Resumen Macro -> Calle
        if df_detalle is None or df_detalle.empty:
            resumen_text.insert(tk.END, "No hay Tasks asociadas al turno actual.\n")
            resumen_text.configure(state="disabled")
        else:
            df_grouped = (
                df_detalle.groupby(["Macro", "Calle"])["PailQuantity"]
                .sum()
                .reset_index()
            )
            df_macro_total = (
                df_detalle.groupby("Macro")["PailQuantity"]
                .sum()
                .reset_index()
            )

            line_count = 0
            for _, mrow in df_macro_total.iterrows():
                macro, total_macro = mrow["Macro"], int(mrow["PailQuantity"])
                resumen_text.insert(tk.END, f"{macro} - Total: {total_macro}\n", "macro")
                line_count += 1
                df_calles = df_grouped[df_grouped["Macro"] == macro]
                for _, crow in df_calles.iterrows():
                    resumen_text.insert(
                        tk.END,
                        f"  {crow['Calle']} - Total: {int(crow['PailQuantity'])}\n",
                        "calle",
                    )
                    line_count += 1
                resumen_text.insert(tk.END, "\n")
                line_count += 1

            resumen_text.tag_configure("macro", font=("Arial", 13, "bold"), foreground="lightblue")
            resumen_text.tag_configure("calle", font=("Arial", 11, "bold"), foreground="white")
            resumen_text.configure(height=line_count + 1, state="disabled")

        # Refrescar informe completo (incluye detalle + totales)
        _generar_informe(df_detalle)

    # Botón de toolbar “Actualizar Cartir”
    def _actualizar_cartir_full():
        _refresh_header_only()
        try:
            _cargar_servidor()
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar: {e}")

    ctk.CTkButton(toolbar, text="Actualizar Cartir", command=_actualizar_cartir_full)\
        .pack(side="left", padx=6)

    # Vista inicial
    _activar("servidor")
    _refresh_header_only()
    _cargar_servidor()
