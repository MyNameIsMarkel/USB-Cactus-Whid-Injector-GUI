"""Punto de entrada: python3 -m whidgui"""

import sys

from PyQt5.QtWidgets import QApplication

from .mainwindow import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("USB Cactus WHID Injector GUI")
    app.setApplicationDisplayName("USB Cactus WHID Injector GUI")
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
