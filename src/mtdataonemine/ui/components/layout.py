# mtdataonemine/ui/components/layout.py
from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk
from mtdataonemine.ui.theme import FONT_TITLE, FONT_SUBTITLE, PAD_X, PAD_Y, BTN_ACTIVE


def build_left_menu_right_panel(parent: ctk.CTkFrame, left_width: int = 200):
    """Crea el layout base con menú a la izquierda y panel dinámico a la derecha."""
    container = ctk.CTkFrame(parent)
    container.pack(fill="both", expand=True)

    left = ctk.CTkFrame(container, width=left_width)
    left.pack(side="left", fill="y", padx=PAD_X, pady=PAD_Y)
    left.pack_propagate(False)

    right = ctk.CTkFrame(container)
    right.pack(side="left", fill="both", expand=True, padx=PAD_X, pady=PAD_Y)

    ctk.CTkLabel(left, text="Menú", font=FONT_TITLE).pack(pady=5)
    return left, right


def page(parent: ctk.CTkFrame):
    """Crea una página con un frame interno para el contenido."""
    page = ctk.CTkFrame(parent)
    inner = ctk.CTkFrame(page)
    inner.pack(fill="both", expand=True, padx=PAD_X, pady=PAD_Y)
    return page, inner


def toolbar(parent: ctk.CTkFrame):
    """Barra de botones superior."""
    bar = ctk.CTkFrame(parent)
    bar.pack(fill="x", padx=PAD_X, pady=(0, PAD_Y))
    return bar


def button_menu(parent: ctk.CTkFrame, text: str, command):
    """Botón para el menú lateral."""
    btn = ctk.CTkButton(parent, text=text, command=command)
    btn.pack(fill="x", pady=5)
    return btn


def title(parent: ctk.CTkFrame, text: str):
    """Título grande."""
    ctk.CTkLabel(parent, text=text, font=FONT_TITLE).pack(anchor="w", pady=(0, 5))


def subtitle(parent: ctk.CTkFrame, text: str):
    """Subtítulo de sección."""
    ctk.CTkLabel(parent, text=text, font=FONT_SUBTITLE).pack(anchor="w", pady=(5, 5))


def tree(parent: ctk.CTkFrame, columns: list[str], height: int = 10):
    """Crea tabla tipo TreeView con scrollbars."""
    frame = ctk.CTkFrame(parent)
    frame.pack(fill="both", expand=True, pady=PAD_Y)

    scroll_y = ttk.Scrollbar(frame, orient="vertical")
    scroll_y.pack(side="right", fill="y")

    scroll_x = ttk.Scrollbar(frame, orient="horizontal")
    scroll_x.pack(side="bottom", fill="x")

    table = ttk.Treeview(
        frame,
        columns=columns,
        show="headings",
        height=height,
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )

    scroll_y.config(command=table.yview)
    scroll_x.config(command=table.xview)

    for c in columns:
        table.heading(c, text=c)
        table.column(c, anchor="center", width=140)

    table.pack(side="left", fill="both", expand=True)
    return table
