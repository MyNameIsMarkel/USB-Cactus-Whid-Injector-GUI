#!/usr/bin/env bash
# Desinstala accesos directos e icono (no borra el repositorio).
set -euo pipefail
APP_ID="usb-cactus-whid-injector-gui"

rm -f "$HOME/.local/share/applications/$APP_ID.desktop"
rm -f "/usr/share/applications/$APP_ID.desktop" 2>/dev/null || true
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/$APP_ID.png"
rm -f "/usr/share/icons/hicolor/256x256/apps/$APP_ID.png" 2>/dev/null || true
for d in "${DESKTOP_DIR:-}" "$HOME/Escritorio" "$HOME/Desktop"; do
    [[ -n "$d" && -f "$d/$APP_ID.desktop" ]] && rm -f "$d/$APP_ID.desktop"
done
update-desktop-database -q "$HOME/.local/share/applications" 2>/dev/null || true
kbuildsycoca6 >/dev/null 2>&1 || kbuildsycoca5 >/dev/null 2>&1 || true
echo "[+] Accesos directos e icono eliminados."
