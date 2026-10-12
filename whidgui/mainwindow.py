"""Ventana principal de USB Cactus WHID Injector GUI."""

from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .ducky import CHEAT_SHEET, DuckyHighlighter
from .flasher import EsptoolRunner, esptool_cmd
from .serialmon import SerialMonitor, available_ports
from .theme import ACCENT, BAD, MUTED, OK, STYLESHEET, WARN

HERE = Path(__file__).resolve().parent
ICON_PNG = HERE / "resources" / "icon.png"
SAMPLES_DIR = HERE / "resources" / "scripts"
USER_SCRIPTS = Path.home() / ".whidgui" / "scripts"

# Valores por defecto de ESPloitV2 (el usuario debería cambiarlos en el panel).
DEFAULT_AP_SSID = "Exploit"
DEFAULT_AP_PASS = "DotAgency"
DEFAULT_PANEL_URL = "http://192.168.1.1"
DEFAULT_ADMIN = "admin / hacktheplanet"


def mono(widget):
    widget.setFont(QFont("DejaVu Sans Mono", 11))
    return widget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.flasher = EsptoolRunner(self)
        self.serial = SerialMonitor(self)
        self._current_script_path: Path | None = None

        self.setWindowTitle("USB Cactus WHID Injector GUI")
        self.setMinimumSize(1080, 700)
        if ICON_PNG.exists():
            self.setWindowIcon(QIcon(str(ICON_PNG)))
        self.setStyleSheet(STYLESHEET)

        USER_SCRIPTS.mkdir(parents=True, exist_ok=True)
        self._build_ui()
        self._wire()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._header())
        root.addWidget(self._banner())

        tabs = QTabWidget()
        tabs.addTab(self._tab_flash(), "Flashear")
        tabs.addTab(self._tab_serial(), "Monitor serie")
        tabs.addTab(self._tab_ducky(), "DuckyScript")
        tabs.addTab(self._tab_panel(), "Panel web")
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(14, 12, 14, 14)
        wl.addWidget(tabs)
        root.addWidget(wrap, 1)

        self.status = self.statusBar()
        self.status.showMessage("Listo.")

    def _header(self):
        header = QFrame(objectName="header")
        h = QHBoxLayout(header)
        h.setContentsMargins(16, 12, 16, 12)
        h.setSpacing(12)
        logo = QLabel()
        if ICON_PNG.exists():
            logo.setPixmap(QPixmap(str(ICON_PNG)).scaled(
                40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        h.addWidget(logo)
        box = QVBoxLayout()
        box.setSpacing(0)
        box.addWidget(QLabel("USB Cactus WHID Injector GUI", objectName="title"))
        box.addWidget(QLabel("Gestión del Cactus WHID (ESP8266 / ESPloitV2)",
                             objectName="subtitle"))
        h.addLayout(box)
        h.addStretch(1)
        et = "esptool: " + " ".join(esptool_cmd()[:1] or ["—"])
        lbl = QLabel(et)
        lbl.setObjectName("subtitle")
        h.addWidget(lbl)
        return header

    def _banner(self):
        b = QFrame(objectName="banner")
        bl = QHBoxLayout(b)
        bl.setContentsMargins(14, 8, 14, 8)
        txt = QLabel("⚠  Herramienta de seguridad. Úsala solo en equipos de tu "
                     "propiedad o con autorización explícita por escrito.")
        txt.setObjectName("bannerText")
        txt.setWordWrap(True)
        bl.addWidget(txt)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(14, 8, 14, 0)
        wl.addWidget(b)
        return wrap

    # ---------------------------------------------------------- Tab: Flash
    def _tab_flash(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        cfg = QGroupBox("Configuración de flasheo")
        g = QGridLayout(cfg)
        g.addWidget(QLabel("Puerto"), 0, 0)
        self.fl_port = QLineEdit("/dev/ttyACM0")
        g.addWidget(self.fl_port, 0, 1)
        g.addWidget(QLabel("Baud"), 0, 2)
        self.fl_baud = QComboBox()
        self.fl_baud.addItems(["115200", "230400", "460800", "921600", "74880"])
        g.addWidget(self.fl_baud, 0, 3)
        g.addWidget(QLabel("Firmware (.bin)"), 1, 0)
        self.fl_fw = QLineEdit()
        self.fl_fw.setPlaceholderText("Ruta al .bin de ESPloitV2 (lo aportas tú)")
        g.addWidget(self.fl_fw, 1, 1, 1, 2)
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self._pick_firmware)
        g.addWidget(browse, 1, 3)
        g.addWidget(QLabel("Offset"), 2, 0)
        self.fl_offset = QLineEdit("0x00000")
        g.addWidget(self.fl_offset, 2, 1)
        v.addWidget(cfg)

        row = QHBoxLayout()
        self.btn_info = QPushButton("Detectar chip")
        self.btn_info.clicked.connect(self._do_chip_info)
        row.addWidget(self.btn_info)
        self.btn_erase = QPushButton("Borrar flash")
        self.btn_erase.setObjectName("danger")
        self.btn_erase.clicked.connect(self._do_erase)
        row.addWidget(self.btn_erase)
        row.addStretch(1)
        self.btn_flash = QPushButton("Flashear firmware")
        self.btn_flash.setObjectName("primary")
        self.btn_flash.clicked.connect(self._do_flash)
        row.addWidget(self.btn_flash)
        self.btn_flash_stop = QPushButton("Detener")
        self.btn_flash_stop.setObjectName("danger")
        self.btn_flash_stop.setEnabled(False)
        self.btn_flash_stop.clicked.connect(self.flasher.stop)
        row.addWidget(self.btn_flash_stop)
        v.addLayout(row)

        self.fl_out = mono(QPlainTextEdit())
        self.fl_out.setReadOnly(True)
        self.fl_out.setPlaceholderText(
            "Salida de esptool.\n\n"
            "Pon el Cactus WHID en modo flasheo según tu placa, selecciona el "
            ".bin y pulsa «Flashear firmware».")
        v.addWidget(self.fl_out, 1)

        note = QLabel(
            "Nota: el .bin de ESPloitV2 lo descargas/compilas tú desde su "
            "repositorio oficial. El microcontrolador 32u4 (parte HID) se "
            "flashea aparte con el IDE de Arduino; esta pestaña cubre la ESP8266.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        v.addWidget(note)
        return w

    # --------------------------------------------------------- Tab: Serial
    def _tab_serial(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Puerto"))
        self.se_port = QComboBox()
        self.se_port.setEditable(True)
        self._refresh_ports()
        top.addWidget(self.se_port, 1)
        refresh = QPushButton("↻")
        refresh.setFixedWidth(40)
        refresh.clicked.connect(self._refresh_ports)
        top.addWidget(refresh)
        top.addWidget(QLabel("Baud"))
        self.se_baud = QComboBox()
        self.se_baud.addItems(["38400", "115200", "9600", "74880"])
        top.addWidget(self.se_baud)
        self.btn_serial = QPushButton("Abrir")
        self.btn_serial.setObjectName("primary")
        self.btn_serial.setFixedWidth(100)
        self.btn_serial.clicked.connect(self._toggle_serial)
        top.addWidget(self.btn_serial)
        v.addLayout(top)

        self.se_out = mono(QPlainTextEdit())
        self.se_out.setReadOnly(True)
        self.se_out.setPlaceholderText("Salida del puerto serie del WHID…")
        v.addWidget(self.se_out, 1)

        quick = QHBoxLayout()
        qb = QPushButton("ResetDefaultConfig:")
        qb.setToolTip("Restaura la configuración por defecto (comando documentado)")
        qb.clicked.connect(lambda: self._serial_send("ResetDefaultConfig:"))
        quick.addWidget(qb)
        quick.addStretch(1)
        v.addLayout(quick)

        row = QHBoxLayout()
        self.se_cmd = QLineEdit()
        self.se_cmd.setPlaceholderText("Escribe un comando y pulsa Enter")
        self.se_cmd.returnPressed.connect(self._serial_send_typed)
        row.addWidget(self.se_cmd, 1)
        send = QPushButton("Enviar")
        send.setObjectName("primary")
        send.setFixedWidth(100)
        send.clicked.connect(self._serial_send_typed)
        row.addWidget(send)
        v.addLayout(row)
        return w

    # ---------------------------------------------------------- Tab: Ducky
    def _tab_ducky(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(10)

        bar = QHBoxLayout()
        for label, fn in [
            ("Nuevo", self._ducky_new),
            ("Abrir…", self._ducky_open),
            ("Guardar", self._ducky_save),
            ("Guardar como…", self._ducky_save_as),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addWidget(QLabel("Ejemplo:"))
        self.sample_box = QComboBox()
        self.sample_box.addItem("— seleccionar —")
        for p in sorted(SAMPLES_DIR.glob("*.txt")):
            self.sample_box.addItem(p.stem, str(p))
        self.sample_box.currentIndexChanged.connect(self._load_sample)
        bar.addWidget(self.sample_box, 1)
        v.addLayout(bar)

        mid = QHBoxLayout()
        left = QVBoxLayout()
        self.editor = mono(QPlainTextEdit())
        self.editor.setPlaceholderText("Escribe aquí tu payload DuckyScript…")
        self.highlighter = DuckyHighlighter(self.editor.document())
        left.addWidget(self.editor, 1)

        ins = QHBoxLayout()
        for token in ["DELAY 500", "STRING ", "ENTER", "GUI r", "TAB", "CTRL ALT DELETE"]:
            b = QPushButton(token.strip())
            b.clicked.connect(lambda _=False, t=token: self._insert_token(t))
            ins.addWidget(b)
        left.addLayout(ins)
        mid.addLayout(left, 2)

        cheat = mono(QPlainTextEdit())
        cheat.setReadOnly(True)
        cheat.setPlainText(CHEAT_SHEET)
        cheat.setFixedWidth(340)
        mid.addWidget(cheat)
        v.addLayout(mid, 1)

        bottom = QHBoxLayout()
        self.ducky_path_lbl = QLabel("Sin guardar")
        self.ducky_path_lbl.setObjectName("hint")
        bottom.addWidget(self.ducky_path_lbl, 1)
        copy = QPushButton("Copiar al portapapeles")
        copy.clicked.connect(self._ducky_copy)
        bottom.addWidget(copy)
        openp = QPushButton("Abrir panel web")
        openp.clicked.connect(self._open_panel)
        bottom.addWidget(openp)
        v.addLayout(bottom)

        hint = QLabel("Para ejecutarlo: sube el script al dispositivo desde su "
                      "panel web (Upload/Choose Payload) o pégalo en «Live "
                      "Payload Mode». Tus scripts se guardan en ~/.whidgui/scripts.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        v.addWidget(hint)
        return w

    # ---------------------------------------------------------- Tab: Panel
    def _tab_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        info = QGroupBox("Datos del dispositivo (ESPloitV2 por defecto)")
        g = QGridLayout(info)
        g.addWidget(QLabel("WiFi (AP)"), 0, 0)
        g.addWidget(self._ro(f"{DEFAULT_AP_SSID}  /  {DEFAULT_AP_PASS}"), 0, 1)
        g.addWidget(QLabel("Panel web"), 1, 0)
        self.panel_url = QLineEdit(DEFAULT_PANEL_URL)
        g.addWidget(self.panel_url, 1, 1)
        g.addWidget(QLabel("Admin"), 2, 0)
        g.addWidget(self._ro(DEFAULT_ADMIN), 2, 1)
        v.addWidget(info)

        btn = QPushButton("Abrir panel web en el navegador")
        btn.setObjectName("primary")
        btn.clicked.connect(self._open_panel)
        v.addWidget(btn)

        warn = QLabel(
            "Pasos: 1) conéctate a la red WiFi del WHID.  2) abre el panel.  "
            "3) cambia YA el SSID, la contraseña del AP y las credenciales de "
            "admin por defecto.\n\nEstos valores son los de fábrica de ESPloitV2 "
            "y son públicos: si no los cambias, cualquiera cerca podría controlar "
            "el dispositivo.")
        warn.setObjectName("hint")
        warn.setWordWrap(True)
        v.addWidget(warn)
        v.addStretch(1)
        return w

    def _ro(self, text):
        e = QLineEdit(text)
        e.setReadOnly(True)
        return e

    # --------------------------------------------------------------- wiring
    def _wire(self):
        self.flasher.output.connect(lambda t: self.fl_out.insertPlainText(t))
        self.flasher.started.connect(self._flash_started)
        self.flasher.finished.connect(self._flash_finished)
        self.flasher.error.connect(lambda m: self._err(self.fl_out, m))

        self.serial.received.connect(lambda line: self.se_out.appendPlainText(line))
        self.serial.connected.connect(self._serial_state)
        self.serial.error.connect(lambda m: self._err(self.se_out, m))

    # ----- flasher actions
    def _pick_firmware(self):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir firmware", "",
                                              "Firmware (*.bin);;Todos (*)")
        if path:
            self.fl_fw.setText(path)

    def _do_flash(self):
        fw = self.fl_fw.text().strip()
        if not fw or not os.path.exists(fw):
            QMessageBox.warning(self, "Firmware", "Selecciona un archivo .bin válido.")
            return
        self.fl_out.appendPlainText(f"\n$ flasheando {os.path.basename(fw)}…\n")
        self.flasher.flash(self.fl_port.text().strip(), self.fl_baud.currentText(),
                           fw, self.fl_offset.text().strip() or "0x00000")

    def _do_erase(self):
        if QMessageBox.question(self, "Borrar flash",
                                "¿Borrar por completo la flash de la ESP8266?") \
                == QMessageBox.Yes:
            self.fl_out.appendPlainText("\n$ erase_flash…\n")
            self.flasher.erase(self.fl_port.text().strip(), self.fl_baud.currentText())

    def _do_chip_info(self):
        self.fl_out.appendPlainText("\n$ flash_id…\n")
        self.flasher.chip_info(self.fl_port.text().strip(), self.fl_baud.currentText())

    def _flash_started(self, _cmd):
        for b in (self.btn_flash, self.btn_erase, self.btn_info):
            b.setEnabled(False)
        self.btn_flash_stop.setEnabled(True)
        self.status.showMessage("esptool en ejecución…")

    def _flash_finished(self, code):
        for b in (self.btn_flash, self.btn_erase, self.btn_info):
            b.setEnabled(True)
        self.btn_flash_stop.setEnabled(False)
        msg = "Completado." if code == 0 else f"esptool terminó con código {code}."
        self.status.showMessage(msg)
        self.fl_out.appendPlainText(f"\n[{'OK' if code==0 else 'ERROR'}] {msg}\n")

    # ----- serial actions
    def _refresh_ports(self):
        cur = self.se_port.currentText() if self.se_port.count() else ""
        self.se_port.clear()
        ports = available_ports()
        self.se_port.addItems(ports or ["/dev/ttyACM0"])
        if cur:
            self.se_port.setEditText(cur)

    def _toggle_serial(self):
        if self.serial.is_open():
            self.serial.close()
        else:
            try:
                baud = int(self.se_baud.currentText())
            except ValueError:
                baud = 38400
            self.serial.open(self.se_port.currentText().strip(), baud)

    def _serial_state(self, is_open):
        self.btn_serial.setText("Cerrar" if is_open else "Abrir")
        self.status.showMessage("Puerto serie abierto." if is_open else "Puerto cerrado.")

    def _serial_send_typed(self):
        txt = self.se_cmd.text().strip()
        if txt:
            self.se_cmd.clear()
            self._serial_send(txt)

    def _serial_send(self, text):
        self.se_out.appendPlainText(f"> {text}")
        self.serial.send(text)

    # ----- ducky actions
    def _insert_token(self, token):
        self.editor.insertPlainText(token + ("\n" if not token.endswith(" ") else ""))
        self.editor.setFocus()

    def _ducky_new(self):
        self.editor.clear()
        self._current_script_path = None
        self.ducky_path_lbl.setText("Sin guardar")

    def _ducky_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir script", str(USER_SCRIPTS),
                                              "DuckyScript (*.txt *.dd);;Todos (*)")
        if path:
            self.editor.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))
            self._current_script_path = Path(path)
            self.ducky_path_lbl.setText(path)

    def _ducky_save(self):
        if self._current_script_path is None:
            self._ducky_save_as()
            return
        self._current_script_path.write_text(self.editor.toPlainText(), encoding="utf-8")
        self.status.showMessage(f"Guardado en {self._current_script_path}")

    def _ducky_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar script",
                                              str(USER_SCRIPTS / "payload.txt"),
                                              "DuckyScript (*.txt);;Todos (*)")
        if path:
            self._current_script_path = Path(path)
            self._ducky_save()
            self.ducky_path_lbl.setText(path)

    def _load_sample(self, idx):
        path = self.sample_box.itemData(idx)
        if path:
            self.editor.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))
            self._current_script_path = None
            self.ducky_path_lbl.setText(f"(ejemplo: {Path(path).name}) — sin guardar")

    def _ducky_copy(self):
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.showMessage("Script copiado al portapapeles.")

    # ----- shared
    def _open_panel(self):
        url = getattr(self, "panel_url", None)
        target = url.text().strip() if url else DEFAULT_PANEL_URL
        QDesktopServices.openUrl(QUrl(target))

    def _err(self, console, message):
        console.appendPlainText(f"[!] {message}")
        self.status.showMessage(message)

    def closeEvent(self, event):
        self.serial.close()
        self.flasher.stop()
        super().closeEvent(event)
