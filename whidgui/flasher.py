"""
flasher.py — Envoltorio de esptool para flashear la ESP8266 del Cactus WHID.

No reimplementa nada: llama a `python3 -m esptool` (o al binario esptool.py)
mediante QProcess, de forma no bloqueante y con la salida en tiempo real.
"""

from __future__ import annotations

import re
import shutil
import sys

from PyQt5.QtCore import QObject, QProcess, pyqtSignal

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def esptool_cmd() -> list[str]:
    """Devuelve la forma de invocar esptool disponible en el sistema."""
    if shutil.which("esptool.py"):
        return ["esptool.py"]
    if shutil.which("esptool"):
        return ["esptool"]
    # Último recurso: como módulo del intérprete actual.
    return [sys.executable, "-m", "esptool"]


class EsptoolRunner(QObject):
    output = pyqtSignal(str)
    started = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: QProcess | None = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.state() != QProcess.NotRunning

    # --- construcción de comandos ---------------------------------------
    def _base(self, port: str, baud: str) -> list[str]:
        cmd = esptool_cmd() + ["--chip", "esp8266"]
        if port and port != "auto":
            cmd += ["--port", port]
        if baud:
            cmd += ["--baud", baud]
        return cmd

    def flash(self, port: str, baud: str, firmware: str, offset: str = "0x00000") -> bool:
        cmd = self._base(port, baud) + [
            "write_flash", "--flash_size", "detect", offset, firmware,
        ]
        return self._start(cmd)

    def erase(self, port: str, baud: str) -> bool:
        return self._start(self._base(port, baud) + ["erase_flash"])

    def chip_info(self, port: str, baud: str) -> bool:
        return self._start(self._base(port, baud) + ["flash_id"])

    # --- ejecución -------------------------------------------------------
    def _start(self, argv: list[str]) -> bool:
        if self.is_running():
            return False
        program, args = argv[0], argv[1:]
        self._proc = QProcess(self)
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._on_read)
        self._proc.finished.connect(self._on_done)
        self._proc.errorOccurred.connect(self._on_err)
        self.started.emit(" ".join(argv))
        self._proc.start(program, args)
        return True

    def stop(self) -> None:
        if self.is_running() and self._proc is not None:
            self._proc.terminate()
            if not self._proc.waitForFinished(1500):
                self._proc.kill()

    def _on_read(self) -> None:
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.output.emit(strip_ansi(data))

    def _on_done(self, code: int, _status) -> None:
        self.finished.emit(int(code))
        self._proc = None

    def _on_err(self, err) -> None:
        if err == QProcess.FailedToStart:
            self.error.emit(
                "No se pudo ejecutar esptool. Instálalo con "
                "'pip install esptool' o 'sudo apt install esptool'."
            )
        else:
            self.error.emit("Error al ejecutar esptool.")
