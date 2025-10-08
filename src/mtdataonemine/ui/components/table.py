# mtdataonemine/ui/components/table.py
from __future__ import annotations
from tkinter import ttk
import pandas as pd


def fill_tree(tree: ttk.Treeview, df: pd.DataFrame | None):
    tree.delete(*tree.get_children())
    if df is None or df.empty:
        return
    for _, row in df.iterrows():
        tree.insert("", "end", values=[row.get(c, "") for c in tree["columns"]])
