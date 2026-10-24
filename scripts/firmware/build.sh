#!/usr/bin/env bash
# ZMK firmware for both halves of urchin++ (phase 8).
#
#   scripts/firmware/build.sh [OUT_DIR]        default firmware/build/out
#
#   OUT_DIR/urchin_pp_left.uf2                 left half (split central, ZMK Studio over USB)
#   OUT_DIR/urchin_pp_right.uf2                right half
#   OUT_DIR/settings_reset_{left,right}.uf2    clears a half's pairings (flash both, then
#                                              the real firmware, to re-pair the halves)
#   OUT_DIR/west-manifest-frozen.yml           every project's exact commit
#
# The board (firmware/boards/urchin_pp, a Zephyr module with the battery driver) and the
# user config (firmware/config: keymap, .conf, west.yml) come from this repo; ZMK, Zephyr
# and zmk-rgbled-widget from the commits pinned in firmware/config/west.yml. The west
# workspace lives in firmware/build/ws (gitignored) and is reused between runs.
#
# Runs inside ZMK's build image ($ZMK_BUILD_IMAGE in toolchain.env): CI uses it as the job
# container; elsewhere, without west on PATH, the script re-runs itself in it via Docker.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/firmware/build/out}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
. "$ROOT/toolchain.env"

if ! command -v west >/dev/null 2>&1; then
  command -v docker >/dev/null 2>&1 || { echo "build.sh: needs west (ZMK's build image) or docker" >&2; exit 1; }
  mkdir -p "$OUT"  # mounted too, so an output directory outside the repo gets the files
  exec docker run --rm -v "$ROOT:$ROOT" -v "$OUT:$OUT" -w "$ROOT" "$ZMK_BUILD_IMAGE" \
    bash "$ROOT/scripts/firmware/build.sh" "$OUT"
fi

python3 "$ROOT/scripts/firmware/gen_board.py" --check

# No .pyc files in the shared workspace: parallel code generators (nanopb) racing to write
# them have left truncated ones that break the next build
export PYTHONDONTWRITEBYTECODE=1

WS="$ROOT/firmware/build/ws"
mkdir -p "$WS/config" "$OUT"
cp "$ROOT/firmware/config/west.yml" "$WS/config/west.yml"
cd "$WS"
[ -d .west ] || west init -l config
west update --narrow --fetch-opt=--filter=tree:0
west zephyr-export >/dev/null
west manifest --freeze --active-only >"$OUT/west-manifest-frozen.yml"

build() {  # NAME BOARD CONFIG_DIR [west build args...] [-- cmake args...]
  local name="$1" board="$2" config="$3"
  shift 3
  echo "== $name ($board)"
  west build -p -s "$WS/zmk/app" -d "$WS/build/$name" -b "$board" "$@" \
    -DZMK_CONFIG="$config" -DZMK_EXTRA_MODULES="$ROOT/firmware"
  cp "$WS/build/$name/zephyr/zmk.uf2" "$OUT/$name.uf2"
}
build urchin_pp_left urchin_pp_left "$ROOT/firmware/config" -S studio-rpc-usb-uart -- -DCONFIG_ZMK_STUDIO=y
build urchin_pp_right urchin_pp_right "$ROOT/firmware/config" --
# settings_reset brings its own keymap and runs without Bluetooth: none of the user config applies
mkdir -p "$WS/no-config"
build settings_reset_left urchin_pp_left "$WS/no-config" -- -DSHIELD=settings_reset
build settings_reset_right urchin_pp_right "$WS/no-config" -- -DSHIELD=settings_reset
ls -la "$OUT"
