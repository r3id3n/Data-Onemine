from __future__ import annotations
import os
import logging
import subprocess
from tkinter import messagebox
from mtdataonemine.config.env_loader import get_env

log = logging.getLogger("mtdataonemine.services.vnc")

def _sanitize_ip(ip: str | None) -> str:
    return (ip or "").replace(" ", "")

def conectar_tightvnc(ip: str | None):
    ip = _sanitize_ip(ip)
    if not ip:
        messagebox.showerror("Error", "IP inválida.")
        log.warning("Intento de conexión TightVNC fallido: IP vacía o inválida.")
        return

    vnc_exe = get_env("VNC_EXE") or r"C:\Program Files\TightVNC\tvnviewer.exe"
    vnc_password = get_env("VNC_PASSWORD") or ""

    if not os.path.exists(vnc_exe):
        err_msg = f"No se encontró el ejecutable de TightVNC en la ruta especificada: {vnc_exe}"
        messagebox.showerror("Error", err_msg)
        log.error(err_msg)
        return

    # Construir el comando con argumentos nativos de línea de comandos de tvnviewer
    # tvnviewer.exe [host] -password=[password] o similar
    cmd = [vnc_exe, ip]
    if vnc_password:
        cmd.append(f"-password={vnc_password}")
    else:
        log.warning("VNC_PASSWORD no está definido en el archivo de entorno (.env).")
        messagebox.showwarning("Atención", "VNC_PASSWORD no está configurado. Es posible que TightVNC solicite la clave manualmente.")

    try:
        log.info(f"Iniciando conexión TightVNC al host: {ip}")
        # Popen en modo asíncrono para no colgar la UI de CustomTkinter
        # startupinfo opcional para evitar mostrar ventana de consola CMD
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(cmd, startupinfo=startupinfo, creationflags=0x08000000)
        else:
            subprocess.Popen(cmd)
            
    except FileNotFoundError as fnf_err:
        err_msg = f"No se pudo encontrar el archivo ejecutable al intentar lanzar VNC: {fnf_err}"
        log.error(err_msg)
        messagebox.showerror("Error", err_msg)
    except subprocess.SubprocessError as sub_err:
        err_msg = f"Ocurrió un error al lanzar el subproceso TightVNC Viewer: {sub_err}"
        log.error(err_msg)
        messagebox.showerror("Error", err_msg)
    except Exception as e:
        err_msg = f"Error inesperado al intentar iniciar TightVNC: {e}"
        log.error(err_msg, exc_info=True)
        messagebox.showerror("Error", err_msg)
