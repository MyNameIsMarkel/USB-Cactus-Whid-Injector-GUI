#!/usr/bin/env bash
# Lanzador de USB Cactus WHID Injector GUI.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -x "$DIR/.venv/bin/python" ]]; then
    PY="$DIR/.venv/bin/python"
else
    PY="$(command -v python3 || true)"
fi
if [[ -z "${PY:-}" ]]; then
    echo "No se encuentra python3. Instálalo: sudo apt install python3" >&2
    exit 1
fi
cd "$DIR"
exec "$PY" -m whidgui "$@"
