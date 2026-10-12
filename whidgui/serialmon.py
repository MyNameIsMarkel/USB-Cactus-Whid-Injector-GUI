"""
serialmon.py — Monitor serie basado en pyserial, en un hilo propio.

Permite abrir el puerto del WHID (por defecto 38400 baud, como documenta
ESPloitV2) para enviar comandos de configuración y ver la salida.
"""

from __future__ import annotations

from PyQt5.QtCore import QObject, QThread, pyqtSignal

try:
    import serial  # pyserial
    from serial.tools import list_ports
    HAVE_SERIAL = True
except Exception:  # pragma: no cover
    HAVE_SERIAL = False


def available_ports() -> list[str]:
    """Lista los puertos serie detectados."""
    if not HAVE_SERIAL:
        return []
    return [p.device for p in list_ports.comports()]


class _ReaderThread(QThread):
    line = pyqtSignal(str)
    closed = pyqtSignal(str)

    def __init__(self, ser):
        super().__init__()
        self._ser = ser
        self._run = True

    def run(self):
        buf = b""
        try:
            while self._run:
                chunk = self._ser.read(256)
                if chunk:
                    buf += chunk
                    while b"\n" in buf:
                        ln, buf = buf.split(b"\n", 1)
                        self.line.emit(ln.decode("utf-8", "replace").rstrip("\r"))
        except Exception as exc:  # puerto desconectado, etc.
            self.closed.emit(str(exc))

    def stop(self):
        self._run = False


class SerialMonitor(QObject):
    received = pyqtSignal(str)
    connected = pyqtSignal(bool)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ser = None
        self._reader: _ReaderThread | None = None

    def is_open(self) -> bool:
        return self._ser is not None and getattr(self._ser, "is_open", False)

    def open(self, port: str, baud: int = 38400) -> None:
        if not HAVE_SERIAL:
            self.error.emit("Falta pyserial. Instálalo: pip install pyserial")
            return
        if self.is_open():
            self.close()
        try:
            self._ser = serial.Serial(port, baud, timeout=0.2)
        except Exception as exc:
            self.error.emit(f"No se pudo abrir {port}: {exc}")
            return
        self._reader = _ReaderThread(self._ser)
        self._reader.line.connect(self.received)
        self._reader.closed.connect(self._on_reader_closed)
        self._reader.start()
        self.connected.emit(True)

    def send(self, text: str, newline: bool = True) -> None:
        if not self.is_open():
            self.error.emit("El puerto no está abierto.")
            return
        data = (text + ("\n" if newline else "")).encode("utf-8", "replace")
        try:
            self._ser.write(data)
        except Exception as exc:
            self.error.emit(f"Error al escribir: {exc}")

    def close(self) -> None:
        if self._reader is not None:
            self._reader.stop()
            self._reader.wait(800)
            self._reader = None
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        self.connected.emit(False)

    def _on_reader_closed(self, msg: str) -> None:
        self.error.emit(f"Conexión serie cerrada: {msg}")
        self.close()
