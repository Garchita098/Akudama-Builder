#!/usr/bin/env bash
# Capture Living Dungeon screenshots without a physical display.
# Uses Xvfb when DISPLAY is unset (plain Linux VMs and GitHub Actions).
# Godot --headless does not render, so this script runs a real GL context.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
GODOT_VERSION="4.4.1"
GODOT_ZIP_NAME="Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip"
GODOT_BIN_NAME="Godot_v${GODOT_VERSION}-stable_linux.x86_64"
GODOT_URL="https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable/${GODOT_ZIP_NAME}"
CACHE_DIR="$PROJECT/.cache/godot"

ORIGINAL_ARGS=("$@")
PRESET="${LIVING_DUNGEON_PRESET:-all}"
SECONDS_SIM="${LIVING_DUNGEON_SECONDS:-3}"
FRAMES="${LIVING_DUNGEON_FRAMES:-}"
SEED="${LIVING_DUNGEON_SEED:-12047}"
OUT="${LIVING_DUNGEON_OUT:-$PROJECT/screenshots}"
CAMERA="${LIVING_DUNGEON_CAMERA:-}"
ZOOM="${LIVING_DUNGEON_ZOOM:-}"
TILE="${LIVING_DUNGEON_TILE:-}"
INSTALL_ONLY=0
FORCE_XVFB="${FORCE_XVFB:-0}"
NO_XVFB=0

usage() {
  cat <<EOF
Usage: tools/screenshot.sh [options]

Run Living Dungeon under Godot ${GODOT_VERSION} and save PNG screenshots.

Options:
  --preset NAME     overview, settlement, units, ui (alias: minimap), custom, or all
                    (default: all)
  --seconds N       Simulated seconds before the shot (default: 3). Ignored when --frames is set.
  --frames N        Process frames to simulate before the shot.
  --seed N          RNG seed applied before world generation (default: 12047). Use "random" to skip.
  --out DIR         Output directory (default: projects/dungeon_godot/screenshots)
  --camera X,Y      World-pixel camera focus. Use with --preset custom.
  --tile X,Y        Tile coordinate focus. Use with --preset custom.
  --zoom Z          Zoom for --preset custom (default in the capture scene: 1.6).
  --godot PATH      Godot 4.4 editor binary. Overrides GODOT and the local cache.
  --install-godot   Download Godot ${GODOT_VERSION} into .cache/godot and exit.
  --xvfb            Always wrap the run in Xvfb.
  --no-xvfb         Do not wrap in Xvfb (requires a working DISPLAY and OpenGL).
  -h, --help        Show this help.

Presets:
  overview     Wide view of the opening map, including the Azure settlement.
  settlement   Close view of the first settlement.
  units        Close view of the densest cluster of living soldiers.
  ui           Default game camera. Header, minimap, and bottom panel stay on screen.
  custom       Frame --camera or --tile at --zoom.

The capture scene is res://tools/screenshot_capture.tscn. It instances the
normal game, so gameplay scripts are not edited for a screenshot run.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --preset) PRESET="$2"; shift 2 ;;
    --seconds) SECONDS_SIM="$2"; shift 2 ;;
    --frames) FRAMES="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --camera) CAMERA="$2"; shift 2 ;;
    --tile) TILE="$2"; shift 2 ;;
    --zoom) ZOOM="$2"; shift 2 ;;
    --godot) GODOT="$2"; shift 2 ;;
    --install-godot) INSTALL_ONLY=1; shift ;;
    --xvfb) FORCE_XVFB=1; shift ;;
    --no-xvfb) NO_XVFB=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

install_godot() {
  local dest="$CACHE_DIR/$GODOT_BIN_NAME"
  if [ -x "$dest" ] && "$dest" --version >/dev/null 2>&1; then
    echo "Godot already installed: $dest"
    "$dest" --version
    return 0
  fi
  mkdir -p "$CACHE_DIR"
  local zip="$CACHE_DIR/$GODOT_ZIP_NAME"
  echo "Downloading $GODOT_URL"
  curl -fL --retry 3 --retry-delay 2 -o "$zip" "$GODOT_URL"
  unzip -o "$zip" -d "$CACHE_DIR"
  chmod +x "$dest"
  if [ ! -x "$dest" ]; then
    echo "Godot binary missing after unzip: $dest" >&2
    exit 1
  fi
  "$dest" --version
}

resolve_godot() {
  if [ -n "${GODOT:-}" ]; then
    if [ ! -x "$GODOT" ]; then
      echo "GODOT is not executable: $GODOT" >&2
      exit 1
    fi
    printf '%s\n' "$GODOT"
    return 0
  fi
  local cached="$CACHE_DIR/$GODOT_BIN_NAME"
  if [ -x "$cached" ]; then
    printf '%s\n' "$cached"
    return 0
  fi
  if command -v godot >/dev/null 2>&1; then
    command -v godot
    return 0
  fi
  if command -v godot4 >/dev/null 2>&1; then
    command -v godot4
    return 0
  fi
  echo "Godot ${GODOT_VERSION} was not found." >&2
  echo "Install it with: $0 --install-godot" >&2
  echo "Or set GODOT to the editor binary." >&2
  exit 1
}

if [ "$INSTALL_ONLY" -eq 1 ]; then
  install_godot
  exit 0
fi

if [ "${SCREENSHOT_XVFB_INNER:-}" != "1" ] && [ "$NO_XVFB" -ne 1 ]; then
  if [ -z "${DISPLAY:-}" ] || [ "$FORCE_XVFB" -eq 1 ]; then
    if ! command -v xvfb-run >/dev/null 2>&1; then
      echo "xvfb-run is required when DISPLAY is unset. Install the xvfb package." >&2
      exit 1
    fi
    export SCREENSHOT_XVFB_INNER=1
    export LIBGL_ALWAYS_SOFTWARE=1
    export GALLIUM_DRIVER=llvmpipe
    export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
    exec xvfb-run -a -s "-screen 0 1280x1600x24" "$0" "${ORIGINAL_ARGS[@]}"
  fi
fi

GODOT_BIN="$(resolve_godot)"
mkdir -p "$OUT"
case "$OUT" in
  /*) ;;
  *) OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")" ;;
esac

USER_ARGS=(--preset "$PRESET" --out "$OUT" --seed "$SEED")
if [ -n "$FRAMES" ]; then
  USER_ARGS+=(--frames "$FRAMES")
else
  USER_ARGS+=(--seconds "$SECONDS_SIM")
fi
if [ -n "$CAMERA" ]; then
  USER_ARGS+=(--camera "$CAMERA")
fi
if [ -n "$TILE" ]; then
  USER_ARGS+=(--tile "$TILE")
fi
if [ -n "$ZOOM" ]; then
  USER_ARGS+=(--zoom "$ZOOM")
fi

LOG="$OUT/capture.log"
CMD=(
  "$GODOT_BIN"
  --path "$PROJECT"
  --resolution 720x1280
  --position 0,0
  --windowed
  --display-driver x11
  --rendering-driver opengl3
  --rendering-method gl_compatibility
  --audio-driver Dummy
  --fixed-fps 20
  --disable-vsync
  res://tools/screenshot_capture.tscn
  --
  "${USER_ARGS[@]}"
)

echo "Running: ${CMD[*]}"
set +e
if command -v timeout >/dev/null 2>&1; then
  timeout 180 "${CMD[@]}" >"$LOG" 2>&1
  status=$?
else
  "${CMD[@]}" >"$LOG" 2>&1
  status=$?
fi
set -e
cat "$LOG"
if [ "$status" -eq 124 ]; then
  echo "Godot screenshot capture timed out after 180s" >&2
  exit 124
fi
if [ "$status" -ne 0 ]; then
  echo "Godot screenshot capture failed with exit $status" >&2
  exit "$status"
fi
if grep -E "SCRIPT ERROR|Parse Error|Failed to load script" "$LOG"; then
  echo "Godot reported a script error during capture" >&2
  exit 1
fi

shopt -s nullglob
pngs=("$OUT"/*.png)
shopt -u nullglob
if [ "${#pngs[@]}" -eq 0 ]; then
  echo "No PNG files were written to $OUT" >&2
  exit 1
fi
python3 "$SCRIPT_DIR/assets.py" check-screenshot "${pngs[@]}"
echo "Screenshots written to $OUT"
