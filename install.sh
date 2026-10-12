#!/usr/bin/env bash
#
# Instalador de USB Cactus WHID Injector GUI.
# - Comprueba dependencias (python3, PyQt5, pyserial, esptool).
# - Registra el icono y crea el acceso directo en el menú (compatible con KDE)
#   y en el Escritorio.
#
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_SRC="$DIR/whidgui/resources/icon.png"
RUN="$DIR/run.sh"
APP_ID="usb-cactus-whid-injector-gui"

ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }

command -v python3 >/dev/null 2>&1 || { err "Falta python3 (sudo apt install python3)."; exit 1; }

PYBIN="python3"
has() { "$PYBIN" -c "import $1" >/dev/null 2>&1; }

# ---- PyQt5 (obligatorio) ----
if ! has PyQt5; then
    warn "Falta PyQt5."
    if command -v apt >/dev/null 2>&1; then
        read -r -p "¿Instalar python3-pyqt5 con apt? [S/n] " a; a=${a:-S}
        [[ "$a" =~ ^[SsYy]$ ]] && sudo apt update && sudo apt install -y python3-pyqt5 || true
    fi
    if ! has PyQt5; then
        warn "Creando entorno virtual local (pip)…"
        python3 -m venv "$DIR/.venv"
        "$DIR/.venv/bin/pip" install --upgrade pip >/dev/null
        "$DIR/.venv/bin/pip" install PyQt5 pyserial esptool
        PYBIN="$DIR/.venv/bin/python"
    fi
fi

# ---- pyserial + esptool (recomendados) ----
NEED=()
has serial  || NEED+=("pyserial")
has esptool || NEED+=("esptool")
if [[ ${#NEED[@]} -gt 0 && "$PYBIN" == "python3" ]]; then
    warn "Faltan: ${NEED[*]}"
    if command -v apt >/dev/null 2>&1; then
        read -r -p "¿Instalar con apt (python3-serial esptool)? [S/n] " a; a=${a:-S}
        [[ "$a" =~ ^[SsYy]$ ]] && sudo apt install -y python3-serial esptool || true
    fi
    has serial  || warn "pyserial sigue ausente: el monitor serie no funcionará hasta instalarlo."
    has esptool || warn "esptool sigue ausente: el flasheador no funcionará hasta instalarlo (pip install esptool)."
fi
ok "Dependencias comprobadas."

chmod +x "$RUN"

# ---- Icono ----
for base in "$HOME/.local/share/icons/hicolor/256x256/apps" \
            "$([[ $EUID -eq 0 ]] && echo /usr/share/icons/hicolor/256x256/apps)"; do
    [[ -z "$base" ]] && continue
    mkdir -p "$base" && cp -f "$ICON_SRC" "$base/$APP_ID.png"
done
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# ---- .desktop (menú) ----
build_desktop() {
    sed -e "s|__EXEC__|$RUN|g" -e "s|__ICON__|$ICON_SRC|g" \
        "$DIR/$APP_ID.desktop.in" > "$1"
    chmod +x "$1"
}

# Como root instalamos en el menú global (KDE lo ve para todos los usuarios);
# si no, en el del usuario actual.
if [[ $EUID -eq 0 && -w /usr/share/applications ]]; then
    MENU_DIR="/usr/share/applications"
else
    MENU_DIR="$HOME/.local/share/applications"
fi
mkdir -p "$MENU_DIR"
build_desktop "$MENU_DIR/$APP_ID.desktop"
update-desktop-database -q "$MENU_DIR" 2>/dev/null || true
ok "Entrada de menú instalada en $MENU_DIR"

# ---- Acceso directo en el Escritorio ----
# Prioridad: variable DESKTOP_DIR > Escritorio existente > Desktop existente > crear Escritorio.
if [[ -z "${DESKTOP_DIR:-}" ]]; then
    if   [[ -d "$HOME/Escritorio" ]]; then DESKTOP_DIR="$HOME/Escritorio"
    elif [[ -d "$HOME/Desktop" ]];    then DESKTOP_DIR="$HOME/Desktop"
    else DESKTOP_DIR="$HOME/Escritorio"
    fi
fi
mkdir -p "$DESKTOP_DIR"
DESK_FILE="$DESKTOP_DIR/$APP_ID.desktop"
build_desktop "$DESK_FILE"
gio set "$DESK_FILE" metadata::trusted true 2>/dev/null || true
ok "Acceso directo creado en: $DESK_FILE"

# ---- Refrescar el menú de KDE ----
kbuildsycoca6 >/dev/null 2>&1 || kbuildsycoca5 >/dev/null 2>&1 || true

echo
ok "Instalación completada."
echo "   Ábrelo desde el menú (busca «Cactus WHID»), el icono del Escritorio,"
echo "   o ejecutando:  $RUN"
