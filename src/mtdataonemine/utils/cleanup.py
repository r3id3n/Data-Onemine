from __future__ import annotations
import os
import time
import threading
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

_CL_TZ = ZoneInfo("America/Santiago")

def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
            logging.info(f"[cleanup] Eliminado: {path}")
        else:
            logging.info(f"[cleanup] No existe: {path}")
    except Exception as e:
        logging.error(f"[cleanup] Error al eliminar {path}: {e}")

def _next_run_time(hour: int, minute: int = 0) -> datetime:
    now = datetime.now(_CL_TZ)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate

def _sleep_until(dt: datetime):
    # dormir en tramos para poder salir limpio si se necesitara
    while True:
        now = datetime.now(_CL_TZ)
        remaining = (dt - now).total_seconds()
        if remaining <= 0:
            break
        time.sleep(min(remaining, 30))  # 30s para no “martillar” el CPU

def _run_cleanup_loop(paths: list[str], hours: tuple[int, int] = (8, 20)):
    """
    Bucle infinito que:
    - Programa el próximo evento a las HH:00 (con TZ CL).
    - A esa hora, borra todos los paths indicados.
    - Repite para el próximo disparo.
    """
    # Pre-run-run
    now = datetime.now(_CL_TZ)
    if now.minute == 0 and now.hour in hours:
        for p in paths:
            _safe_remove(p)

    idx = 0  # alternar 8 ↔ 20
    while True:
        target_hour = hours[idx % len(hours)]
        idx += 1
        target_dt = _next_run_time(target_hour, 0)
        _sleep_until(target_dt)
        # Ejecutar borrado
        ts = datetime.now(_CL_TZ).strftime("%Y-%m-%d %H:%M:%S %z")
        logging.info(f"[cleanup] Ejecutando limpieza programada ({ts})")
        for p in paths:
            _safe_remove(p)

def start_daily_log_reset(paths: list[str] | None = None, hours: tuple[int, int] = (8, 20)) -> threading.Thread:
    """
    Lanza el hilo daemon que borra `paths` cada día a las HH:00 indicadas.
    Devuelve el hilo, por si quieres guardarlo.
    """
    if not paths:
        desktop_app_dir = Path.home() / "Desktop" / "app"
        paths = [
            str(desktop_app_dir / "listado_actual.txt"),
            str(desktop_app_dir / "equipos_completados.txt"),
        ]
    t = threading.Thread(target=_run_cleanup_loop, args=(paths, hours), daemon=True)
    t.start()
    return t
