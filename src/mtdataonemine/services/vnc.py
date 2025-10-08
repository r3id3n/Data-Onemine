from __future__ import annotations
import os, time, logging
import pyautogui, pygetwindow as gw
from tkinter import messagebox
from mtdataonemine.config.env_loader import get_env

def _sanitize_ip(ip: str|None) -> str:
    return (ip or "").replace(" ", "")

def _wait_for_window(title_substr: str, attempts=12, delay=0.5):
    for _ in range(attempts):
        wins = gw.getWindowsWithTitle(title_substr)
        if wins: return wins
        time.sleep(delay)
    return []

def conectar_tightvnc(ip: str|None):
    ip = _sanitize_ip(ip)
    if not ip:
        messagebox.showerror("Error","IP inválida.")
        return

    vnc_exe = get_env("VNC_EXE") or r"C:\Program Files\TightVNC\tvnviewer.exe"
    vnc_password = get_env("VNC_PASSWORD") or ""

    if not os.path.exists(vnc_exe):
        messagebox.showerror("Error", f"No se encontró TightVNC: {vnc_exe}")
        return

    try:
        os.startfile(vnc_exe)
        time.sleep(1.5)

        w = _wait_for_window("New TightVNC Connection")
        if not w: 
            messagebox.showerror("Error","No se detectó ventana de conexión.")
            return
        try: w[0].activate()
        except Exception: pass
        time.sleep(0.2)

        pyautogui.write(ip); time.sleep(0.2); pyautogui.press("enter"); time.sleep(1.5)

        a = _wait_for_window("Vnc Authentication")
        if not a:
            messagebox.showerror("Error","No se detectó autenticación.")
            return
        try: a[0].activate()
        except Exception: pass
        time.sleep(0.2)
        if not vnc_password:
            messagebox.showwarning("Atención","VNC_PASSWORD no definido.")
        pyautogui.write(vnc_password or ""); time.sleep(0.2); pyautogui.press("enter")
    except Exception as e:
        logging.error(f"VNC: {e}")
        messagebox.showerror("Error", f"No se pudo iniciar TightVNC: {e}")
