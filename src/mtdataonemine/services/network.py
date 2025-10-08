from __future__ import annotations
import os
import platform
import re
import shutil
import subprocess
import threading
import time
from typing import Optional, Callable, List

# ---------- Resolver ping.exe de forma robusta ----------
def _resolve_ping_path() -> str:
    """
    Encuentra ping.exe en Windows (PATH -> System32 -> Sysnative).
    En otros SO retorna 'ping' y deja que el sistema lo resuelva.
    """
    if platform.system().lower().startswith("win"):
        p = shutil.which("ping")
        if p and os.path.exists(p):
            return p
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
        cand1 = os.path.join(windir, "System32", "PING.EXE")
        cand2 = os.path.join(windir, "Sysnative", "PING.EXE")  # procesos 32-bit en Win 64-bit
        if os.path.exists(cand1):
            return cand1
        if os.path.exists(cand2):
            return cand2
        return "ping"
    return "ping"

_PING_BIN = _resolve_ping_path()
_IS_WIN = platform.system().lower().startswith("win")
_CREATE_NO_WINDOW = 0x08000000 if _IS_WIN else 0

def _startup_params_for_os():
    """Evita ventana de consola en Windows."""
    params = {}
    if _IS_WIN:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        params["startupinfo"] = si
        params["creationflags"] = _CREATE_NO_WINDOW
    return params

def _ping_cmd_once(ip: str) -> List[str]:
    return [_PING_BIN, "-n", "1", "-w", "800", ip] if _IS_WIN else [_PING_BIN, "-c", "1", "-W", "1", ip]

def _ping_cmd_continuous(ip: str) -> List[str]:
    return [_PING_BIN, "-t", ip] if _IS_WIN else [_PING_BIN, ip]

# ---------- API simple ----------
def ping_host(ip: str) -> bool:
    """Ping único: True si responde, False si no."""
    try:
        rc = subprocess.run(
            _ping_cmd_once(ip),
            capture_output=True,
            text=True,
            timeout=1.2,
            **_startup_params_for_os(),
        ).returncode
        return rc == 0
    except Exception:
        return False

def ping_once(ip: str, timeout_sec: float = 1.2) -> tuple[bool, Optional[float]]:
    """
    Ping único con latencia estimada.
    Retorna (ok, latency_ms) — latency_ms puede ser None si no se pudo parsear.
    """
    try:
        proc = subprocess.run(
            _ping_cmd_once(ip),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            **_startup_params_for_os(),
        )
        ok = (proc.returncode == 0)
        if not ok:
            return False, None

        out = (proc.stdout or "") + (proc.stderr or "")
        # Windows: "Tiempo=12ms" / "time=12ms"
        # Unix: "time=12.3 ms"
        m = re.search(r"[Tt]i?me[=<]\s*([\d\.]+)\s*ms", out)
        latency = float(m.group(1)) if m else None
        return True, latency
    except Exception:
        return False, None

# ---------- Ping continuo ----------
class PingRunner:
    """
    Ejecuta ping continuo en un hilo y emite líneas al callback.
    - on_line(str): recibe cada línea cruda del proceso
    - on_stop(): llamado al finalizar
    """
    def __init__(self, ip: str, on_line: Callable[[str], None], on_stop: Optional[Callable[[], None]] = None):
        self.ip = ip
        self.on_line = on_line
        self.on_stop = on_stop
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_evt.set()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=0.5)
                except Exception:
                    self._proc.kill()
            except Exception:
                pass
        time.sleep(0.2)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _run(self):
        try:
            popen_kwargs = dict(
                args=_ping_cmd_continuous(self.ip),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding=("mbcs" if _IS_WIN else "utf-8"),  # robusto para ES-CL en Windows
                errors="replace",
                bufsize=1,  # line-buffered
                **_startup_params_for_os(),
            )
            self._proc = subprocess.Popen(**popen_kwargs)

            if self._proc.stdout is None:
                self.on_line("[ping] no hay stdout del proceso")
                return

            for raw in self._proc.stdout:
                if self._stop_evt.is_set():
                    break
                line = (raw or "").rstrip("\r\n")
                if line:
                    self.on_line(line)

        except Exception as e:
            self.on_line(f"[ping] error: {e}")
        finally:
            if self.on_stop:
                self.on_stop()
            self._proc = None
