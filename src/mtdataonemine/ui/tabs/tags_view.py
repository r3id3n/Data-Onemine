from __future__ import annotations
import customtkinter as ctk

from mtdataonemine.ui.tabs.rssi_view import build_rssi_tab
from mtdataonemine.ui.tabs.zanjas_unique_view import build_zanjas_unique_tab
from mtdataonemine.ui.tabs.calle_view import build_calle_tab


def build_tags_tab(
    parent: ctk.CTkFrame,
    get_selected_ip_cb,
    get_selected_combo_text_cb=None,  # opcional
):
    """
    Pestaña 'Tag's' con layout tipo Cartir:
      - Menú lateral (RSSI / Zanjas / Calle)
      - Panel derecho con páginas conmutables
      - Mantiene el padding superior que indicaste
    """

    # Contenedor principal (mismo padding que ya usabas)
    container = ctk.CTkFrame(parent)
    container.pack(fill="both", expand=True)

    # Menú izquierdo (sin pack_propagate(False) para que NO quede ancho)
    # Si lo quieres aún más angosto, baja width a 160 o 150.
    left = ctk.CTkFrame(container, width=180)
    left.pack(side="left", fill="y", padx=10, pady=10)
    # left.pack_propagate(False)   # <- QUITADO para que el ancho se adapte al contenido

    # Panel derecho
    right = ctk.CTkFrame(container)
    right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    # Título del menú
    ctk.CTkLabel(left, text="Menú", font=("Arial", 16, "bold")).pack(pady=(0, 10))

    # Páginas
    page_rssi   = ctk.CTkFrame(right)
    page_zanjas = ctk.CTkFrame(right)
    page_calle  = ctk.CTkFrame(right)

    # Wrapper interno con padding inferior, sin aumentar el margen superior
    def _wrap(page: ctk.CTkFrame) -> ctk.CTkFrame:
        inner = ctk.CTkFrame(page)
        inner.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        return inner

    rssi_inner   = _wrap(page_rssi)
    zanjas_inner = _wrap(page_zanjas)
    calle_inner  = _wrap(page_calle)

    # Construcción de sub-vistas
    build_rssi_tab(rssi_inner, get_selected_ip_cb=get_selected_ip_cb)
    build_zanjas_unique_tab(zanjas_inner, get_selected_ip_cb=get_selected_ip_cb)
    build_calle_tab(calle_inner)

    # Conmutador de páginas (igual estilo que Cartir)
    botones: dict[str, ctk.CTkButton] = {}

    def _mostrar(nombre: str):
        for p in (page_rssi, page_zanjas, page_calle):
            p.pack_forget()
        for b in botones.values():
            b.configure(fg_color="transparent")

        if nombre == "rssi":
            page_rssi.pack(fill="both", expand=True)
        elif nombre == "zanjas":
            page_zanjas.pack(fill="both", expand=True)
        else:
            page_calle.pack(fill="both", expand=True)

        botones[nombre].configure(fg_color=("#3B82F6", "#1E40AF"))

    def _add_btn(key: str, text: str, target: str):
        btn = ctk.CTkButton(left, text=text, command=lambda: _mostrar(target))
        btn.pack(fill="x", pady=5)
        botones[key] = btn

    _add_btn("rssi",   "RSSI",   "rssi")
    _add_btn("zanjas", "Zanjas", "zanjas")
    _add_btn("calle",  "Calle",  "calle")

    # Página por defecto
    _mostrar("rssi")
