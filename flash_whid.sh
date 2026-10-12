#!/usr/bin/env bash
#
# flash_whid.sh — Flasheo completo del Cactus WHID (ESPloitV2) con arduino-cli.
#
# Automatiza los 4 pasos del flasheo sin abrir el IDE de Arduino:
#   1) passthrough  -> sube 'esp8266Programmer' al 32u4 (pone la ESP en modo flash)
#   2) buildesp     -> compila ESP_Code y genera el .bin de la ESP8266
#   3) flashesp     -> flashea ese .bin en la ESP con esptool
#   4) restore      -> sube 'Arduino_32u4_code' al 32u4 (firmware final)
#
# Uso:
#   ./flash_whid.sh all           # hace setup + los 4 pasos, con pausas
#   ./flash_whid.sh setup         # instala arduino-cli, cores, librerías y clona el repo
#   ./flash_whid.sh passthrough   # solo el paso 1
#   ./flash_whid.sh buildesp      # solo el paso 2
#   ./flash_whid.sh flashesp      # solo el paso 3
#   ./flash_whid.sh restore       # solo el paso 4
#   ./flash_whid.sh menuopts      # muestra las opciones de FQBN de la ESP (para depurar)
#
# Variables de entorno para ajustar (con sus valores por defecto):
#   PORT=/dev/ttyACM0
#   ESP_BAUD=115200
#   FQBN_ESP=esp8266:esp8266:generic:eesz=4M3M
#   FQBN_32U4=arduino:avr:LilyPadUSB
#
# ⚠ Usa el dispositivo solo en equipos propios o con autorización explícita.
#
set -euo pipefail

# ----------------------------- configuración ------------------------------
PORT="${PORT:-/dev/ttyACM0}"
ESP_BAUD="${ESP_BAUD:-115200}"
# Vacío = autodetectar la opción de tamaño de flash según el core instalado
# (en el core 2.3.0 es 'FlashSize', en los nuevos 'eesz'). Puedes forzarlo:
#   FQBN_ESP=esp8266:esp8266:generic:FlashSize=4M3M
FQBN_ESP="${FQBN_ESP:-}"
FQBN_32U4="${FQBN_32U4:-arduino:avr:LilyPadUSB}"

WORKDIR="${WORKDIR:-$HOME/.whidgui/esploit}"
REPO_URL="https://github.com/exploitagency/ESPloitV2.git"
REPO_DIR="$WORKDIR/ESPloitV2"
FTP_ZIP_URL="https://github.com/exploitagency/esp8266FTPServer/archive/feature/bbx10_speedup.zip"
ESP_INDEX_URL="http://arduino.esp8266.com/stable/package_esp8266com_index.json"
ESP_CORE_VER="2.3.0"
ARDUINOJSON_VER="5.11.0"
ESP_BUILD="$WORKDIR/esp_build"

ok()   { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
info() { printf '\033[1;36m[*]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; }
pause(){ read -r -p "$(printf '\033[1;35m[>]\033[0m %s ' "$*")" _; }

ACLI="arduino-cli"
ESPTOOL=()

# ----------------------------- utilidades ---------------------------------
detect_esptool() {
    if command -v esptool.py >/dev/null 2>&1;  then ESPTOOL=(esptool.py)
    elif command -v esptool >/dev/null 2>&1;   then ESPTOOL=(esptool)
    else ESPTOOL=(python3 -m esptool); fi
}

ensure_cli() {
    if command -v arduino-cli >/dev/null 2>&1; then
        ACLI="arduino-cli"; return
    fi
    if [[ -x "$HOME/.local/bin/arduino-cli" ]]; then
        ACLI="$HOME/.local/bin/arduino-cli"; return
    fi
    warn "arduino-cli no está instalado."
    read -r -p "¿Instalarlo ahora en ~/.local/bin? [S/n] " a; a=${a:-S}
    if [[ "$a" =~ ^[SsYy]$ ]]; then
        mkdir -p "$HOME/.local/bin"
        curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
            | BINDIR="$HOME/.local/bin" sh
        ACLI="$HOME/.local/bin/arduino-cli"
        ok "arduino-cli instalado."
    else
        err "Necesito arduino-cli para continuar."
        exit 1
    fi
}

check_port() {
    if [[ ! -e "$PORT" ]]; then
        warn "No existe $PORT. Conecta el WHID o ajusta PORT=/dev/ttyXXX."
        warn "Pista: ejecuta 'dmesg | tail' al enchufarlo para ver el puerto."
        return 1
    fi
    # ModemManager suele robar el puerto en Kali.
    if systemctl is-active --quiet ModemManager 2>/dev/null; then
        warn "ModemManager está activo y puede bloquear el puerto."
        read -r -p "¿Pararlo mientras flasheamos? [S/n] " a; a=${a:-S}
        [[ "$a" =~ ^[SsYy]$ ]] && sudo systemctl stop ModemManager || true
    fi
}

# ----------------------------- pasos --------------------------------------
do_setup() {
    ensure_cli
    info "Configurando arduino-cli (índice ESP8266 e instalación insegura de libs)…"
    "$ACLI" config init --overwrite >/dev/null 2>&1 || true
    "$ACLI" config add board_manager.additional_urls "$ESP_INDEX_URL" 2>/dev/null \
        || "$ACLI" config set board_manager.additional_urls "$ESP_INDEX_URL"
    "$ACLI" config set library.enable_unsafe_install true
    "$ACLI" core update-index

    info "Instalando cores (AVR para el 32u4 y ESP8266 $ESP_CORE_VER)…"
    "$ACLI" core install arduino:avr
    "$ACLI" core install "esp8266:esp8266@$ESP_CORE_VER"

    info "Instalando librerías (ArduinoJson $ARDUINOJSON_VER + FTP bbx10)…"
    "$ACLI" lib install "ArduinoJson@$ARDUINOJSON_VER"
    local tmpzip="$WORKDIR/ftp_bbx10.zip"
    mkdir -p "$WORKDIR"
    curl -fsSL "$FTP_ZIP_URL" -o "$tmpzip"
    "$ACLI" lib install --zip-path "$tmpzip"

    info "Clonando ESPloitV2…"
    if [[ -d "$REPO_DIR/.git" ]]; then
        git -C "$REPO_DIR" pull --ff-only || true
    else
        git clone --depth 1 "$REPO_URL" "$REPO_DIR"
    fi
    ok "Setup completado."
}

do_passthrough() {
    check_port || return 1
    local sk="$REPO_DIR/flashing/esp8266Programmer"
    [[ -d "$sk" ]] || { err "No encuentro $sk. Ejecuta primero: $0 setup"; return 1; }
    info "Paso 1/4 — subiendo passthrough al 32u4 ($FQBN_32U4)…"
    "$ACLI" compile --fqbn "$FQBN_32U4" "$sk"
    "$ACLI" upload -p "$PORT" --fqbn "$FQBN_32U4" "$sk"
    ok "Passthrough cargado: la ESP8266 queda en modo programación."
    sleep 2
}

flash_opt() {
    # Devuelve la opción de tamaño de flash correcta para el core instalado.
    local d
    d="$("$ACLI" board details --fqbn esp8266:esp8266:generic 2>/dev/null || true)"
    if   grep -qi "eesz"     <<<"$d"; then echo "eesz=4M3M"
    elif grep -qi "FlashSize" <<<"$d"; then echo "FlashSize=4M3M"
    else echo ""; fi
}

do_buildesp() {
    local sk="$REPO_DIR/source/ESP_Code"
    [[ -d "$sk" ]] || { err "No encuentro $sk. Ejecuta primero: $0 setup"; return 1; }
    local fqbn="$FQBN_ESP"
    if [[ -z "$fqbn" ]]; then
        local opt; opt="$(flash_opt)"
        fqbn="esp8266:esp8266:generic${opt:+:$opt}"
    fi
    info "Paso 2/4 — compilando ESP_Code ($fqbn)…"
    mkdir -p "$ESP_BUILD"
    "$ACLI" compile --fqbn "$fqbn" --output-dir "$ESP_BUILD" "$sk"
    local bin
    bin="$(ls -1 "$ESP_BUILD"/*.bin 2>/dev/null | head -1 || true)"
    [[ -n "$bin" ]] || { err "No se generó el .bin. Revisa los errores de compilación."; return 1; }
    ok "Binario de la ESP generado: $bin"
}

do_flashesp() {
    check_port || return 1
    detect_esptool
    local bin
    bin="$(ls -1 "$ESP_BUILD"/*.bin 2>/dev/null | head -1 || true)"
    [[ -n "$bin" ]] || { err "No hay .bin. Ejecuta antes: $0 buildesp"; return 1; }
    info "Paso 3/4 — flasheando la ESP con esptool ($bin)…"
    "${ESPTOOL[@]}" --chip esp8266 --port "$PORT" --baud "$ESP_BAUD" \
        write_flash --flash_size detect 0x00000 "$bin"
    ok "ESP8266 flasheada."
    sleep 2
}

do_restore() {
    check_port || return 1
    local sk="$REPO_DIR/source/Arduino_32u4_code"
    [[ -d "$sk" ]] || sk="$REPO_DIR/source/Arduino_32u4_Code"
    [[ -d "$sk" ]] || { err "No encuentro el sketch del 32u4. Ejecuta: $0 setup"; return 1; }
    info "Paso 4/4 — subiendo el firmware final al 32u4…"
    "$ACLI" compile --fqbn "$FQBN_32U4" "$sk"
    "$ACLI" upload -p "$PORT" --fqbn "$FQBN_32U4" "$sk"
    ok "Firmware del 32u4 restaurado."
}

do_all() {
    cat <<'BANNER'

  ┌──────────────────────────────────────────────┐
  │   Flasheo completo del Cactus WHID (ESPloitV2) │
  └──────────────────────────────────────────────┘
BANNER
    warn "Úsalo solo en hardware propio o con autorización explícita."
    echo
    do_setup
    pause "Setup listo. Conecta el WHID y pulsa Enter para el PASO 1 (passthrough)…"
    do_passthrough
    pause "Pulsa Enter para el PASO 2 (compilar ESP_Code)…"
    do_buildesp
    pause "Pulsa Enter para el PASO 3 (flashear la ESP)…"
    do_flashesp
    pause "Pulsa Enter para el PASO 4 (restaurar firmware del 32u4)…"
    do_restore
    echo
    ok "¡Hecho! El WHID debería crear ahora su WiFi (SSID 'Exploit' / 'DotAgency')."
    ok "Abre el panel en http://192.168.1.1 (admin/hacktheplanet) y CAMBIA las credenciales."
}

menuopts() {
    ensure_cli
    "$ACLI" board details --fqbn esp8266:esp8266:generic 2>/dev/null \
        | sed -n '/Option/,$p' || warn "Instala primero el core: $0 setup"
}

# ----------------------------- dispatch -----------------------------------
case "${1:-all}" in
    all)         do_all ;;
    setup)       do_setup ;;
    passthrough) ensure_cli; do_passthrough ;;
    buildesp)    ensure_cli; do_buildesp ;;
    flashesp)    do_flashesp ;;
    restore)     ensure_cli; do_restore ;;
    menuopts)    menuopts ;;
    *) err "Opción desconocida: $1";
       echo "Usa: $0 {all|setup|passthrough|buildesp|flashesp|restore|menuopts}"; exit 1 ;;
esac
