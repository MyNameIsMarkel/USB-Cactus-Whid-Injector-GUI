"""
ducky.py — Resaltado de sintaxis y referencia de DuckyScript.

DuckyScript es el lenguaje de payloads de inyección de pulsaciones. Aquí solo
se ofrece ayuda de edición (resaltado + chuleta + comandos para insertar); el
contenido de los payloads lo escribe el usuario.
"""

from __future__ import annotations

from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from .theme import ACCENT, MUTED, WARN

# Comandos más habituales de DuckyScript.
COMMANDS = [
    "REM", "STRING", "STRINGLN", "DELAY", "DEFAULTDELAY", "DEFAULT_DELAY",
    "ENTER", "GUI", "WINDOWS", "MENU", "APP", "SHIFT", "ALT", "CONTROL",
    "CTRL", "TAB", "ESCAPE", "ESC", "SPACE", "BACKSPACE", "DELETE",
    "CAPSLOCK", "HOME", "END", "INSERT", "PAGEUP", "PAGEDOWN",
    "UP", "DOWN", "LEFT", "RIGHT", "UPARROW", "DOWNARROW", "LEFTARROW",
    "RIGHTARROW", "REPEAT", "PRINTSCREEN",
]

CHEAT_SHEET = """CHULETA DE DUCKYSCRIPT
──────────────────────────────
REM <texto>          Comentario (no se ejecuta)
DELAY <ms>           Espera en milisegundos
DEFAULTDELAY <ms>    Espera por defecto entre líneas
STRING <texto>       Escribe el texto tal cual
ENTER                Pulsa Intro
GUI <tecla>          Tecla Windows/Super (GUI r = Ejecutar)
CTRL / ALT / SHIFT   Modificadores (CTRL ALT DELETE)
TAB  ESC  SPACE      Teclas sueltas
UP DOWN LEFT RIGHT   Flechas
REPEAT <n>           Repite la línea anterior n veces

Ejemplo mínimo:
  DELAY 1000
  GUI r
  DELAY 400
  STRING notepad
  ENTER

Consejo: empieza siempre con un DELAY para dar tiempo a que
el sistema reconozca el teclado USB.
"""


class DuckyHighlighter(QSyntaxHighlighter):
    """Colorea comandos, comentarios y números de un payload DuckyScript."""

    def __init__(self, document):
        super().__init__(document)

        self._cmd_fmt = QTextCharFormat()
        self._cmd_fmt.setForeground(QColor(ACCENT))
        self._cmd_fmt.setFontWeight(QFont.Bold)

        self._rem_fmt = QTextCharFormat()
        self._rem_fmt.setForeground(QColor(MUTED))
        self._rem_fmt.setFontItalic(True)

        self._num_fmt = QTextCharFormat()
        self._num_fmt.setForeground(QColor(WARN))

        # Comando al principio de la línea.
        self._cmd_rx = QRegExp(r"^\s*(" + "|".join(COMMANDS) + r")\b")
        self._num_rx = QRegExp(r"\b\d+\b")

    def highlightBlock(self, text: str) -> None:
        stripped = text.lstrip()
        if stripped.startswith("REM"):
            self.setFormat(0, len(text), self._rem_fmt)
            return
        # Números
        idx = self._num_rx.indexIn(text, 0)
        while idx >= 0:
            length = self._num_rx.matchedLength()
            self.setFormat(idx, length, self._num_fmt)
            idx = self._num_rx.indexIn(text, idx + length)
        # Comando inicial
        if self._cmd_rx.indexIn(text) >= 0:
            start = self._cmd_rx.pos(1)
            length = len(self._cmd_rx.cap(1))
            self.setFormat(start, length, self._cmd_fmt)
