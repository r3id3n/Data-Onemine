import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from mtdataonemine.services.network import ping_once, PingRunner

class PingPanel(ctk.CTkFrame):
    def __init__(self, master, get_selected_ip_cb, **kwargs):
        super().__init__(master, **kwargs)
        self.get_selected_ip_cb = get_selected_ip_cb
        self.runner: PingRunner | None = None

        # Etiqueta de estado
        self.status = tk.StringVar(value="Seleccione una máquina para ping / VNC")
        ctk.CTkLabel(self, textvariable=self.status, anchor="w").pack(padx=12, fill="x")

        # Consola (solo UI, NO consola del sistema)
        self.output = ctk.CTkTextbox(self, height=140)
        self.output.pack(padx=12, pady=8, fill="x")
        self.output.configure(state="disabled")

        # Si el frame se destruye, detener el ping
        self.bind("<Destroy>", self._on_destroy, add="+")  # add="+" para no sobreescribir otros binds

    # --- helpers de UI (siempre ejecutados en el hilo principal) ---
    def _append(self, text: str):
        self.output.configure(state="normal")
        ts = datetime.now().strftime("[%H:%M:%S] ")
        self.output.insert(tk.END, ts + text + "\n")
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def _clear(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")

    # --- ciclo de vida ---
    def _on_destroy(self, _evt=None):
        # Evita carreras si el widget ya no existe
        try:
            self.stop()
        except Exception:
            pass

    # --- control del ping ---
    def _start(self, ip: str):
        # Detenemos si había uno
        self.stop()

        # Limpiar consola y arrancar
        self._clear()
        self._append(f"▶️ Ping a {ip} iniciado…")

        # IMPORTANTÍSIMO: redirigir callbacks al hilo principal con after(0, ...)
        self.runner = PingRunner(
            ip=ip,
            on_line=lambda line: self.after(0, self._append, line),
            on_stop=lambda: self.after(0, self._append, "⛔ Ping detenido.")
        )
        self.runner.start()

    def stop(self):
        if self.runner and self.runner.is_running():
            self.runner.stop()
        self.runner = None

    def on_combo_change(self):
        """Se llama automáticamente cuando el usuario elige un equipo en el combobox."""
        ip = self.get_selected_ip_cb()
        if not ip:
            self.status.set("⚠️ Selección inválida")
            self.stop()
            return

        # Ping único para feedback inmediato
        ok, latency = ping_once(ip, timeout_sec=1.2)
        self.status.set(
            f"Ping {ip}: {'OK ✅' if ok else 'FALLÓ ❌'}"
            + (f" ({latency:.1f} ms)" if ok and latency is not None else "")
        )

        # Arranca ping continuo a esa IP (sin botones)
        self._start(ip)
