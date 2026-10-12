"""Hoja de estilo (QSS) — tema oscuro con acento verde cactus."""

BG = "#0f1510"
PANEL = "#161e17"
PANEL_2 = "#1e2a20"
BORDER = "#2c3a2e"
TEXT = "#e8f0e8"
MUTED = "#8ca08f"
ACCENT = "#5ac85a"       # verde cactus
ACCENT_DK = "#46a846"
CONSOLE_BG = "#0a0f0a"
CONSOLE_TEXT = "#cdeccd"
OK = "#5ac85a"
BAD = "#ef5350"
WARN = "#f5a623"

STYLESHEET = f"""
* {{
    font-family: "Inter", "Segoe UI", "Cantarell", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QMainWindow, QWidget#central {{ background: {BG}; }}

QFrame#header {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
QLabel#title {{ font-size: 17px; font-weight: 700; color: {TEXT}; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}

QFrame#banner {{
    background: rgba(245,166,35,0.10);
    border: 1px solid rgba(245,166,35,0.45);
    border-radius: 8px;
}}
QLabel#bannerText {{ color: {WARN}; font-size: 12px; }}

QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding: 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    left: 12px; padding: 0 4px; color: {ACCENT};
}}

QPushButton {{
    background: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    color: {TEXT};
}}
QPushButton:hover {{ border-color: {ACCENT}; background: #26352a; }}
QPushButton:pressed {{ background: #2d3f31; }}
QPushButton:disabled {{ color: {MUTED}; background: {PANEL}; }}

QPushButton#primary {{
    background: {ACCENT}; color: #07130a; font-weight: 700; border: none;
}}
QPushButton#primary:hover {{ background: {ACCENT_DK}; }}
QPushButton#primary:disabled {{ background: #2f4a33; color: #6f8a74; }}

QPushButton#danger {{
    background: transparent; border: 1px solid {BAD}; color: {BAD};
}}
QPushButton#danger:hover {{ background: rgba(239,83,80,0.12); }}

QPlainTextEdit, QTextEdit {{
    background: {CONSOLE_BG};
    color: {CONSOLE_TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", "Consolas", monospace;
    font-size: 12.5px;
    padding: 10px;
    selection-background-color: {ACCENT_DK};
}}

QLineEdit, QComboBox {{
    background: {CONSOLE_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 10px;
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{
    background: {PANEL_2}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_DK}; color: {TEXT};
}}

QTabWidget::pane {{
    border: 1px solid {BORDER}; border-radius: 10px; top: -1px; background: {PANEL};
}}
QTabBar::tab {{
    background: transparent; color: {MUTED};
    padding: 9px 18px; border: none; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}

QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QStatusBar::item {{ border: none; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QLabel#hint {{ color: {MUTED}; font-size: 12px; }}
"""
