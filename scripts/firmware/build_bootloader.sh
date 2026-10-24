#!/usr/bin/env bash
# Adafruit nRF52 UF2 bootloader for urchin++ (phase 8): one build serves both halves.
#
#   scripts/firmware/build_bootloader.sh [OUT_DIR]     default firmware/build/out
#
#   OUT_DIR/urchin_pp_bootloader-<ver>_s140_6.1.1.hex   MBR + SoftDevice S140 6.1.1 + bootloader:
#                                                       the one-time flash over SWD (TP2)
#   OUT_DIR/update-urchin_pp_bootloader-<ver>_nosd.uf2  later bootloader updates over UF2
#
# The bootloader source is Adafruit_nRF52_Bootloader at $ADAFRUIT_BOOTLOADER_VERSION
# (commit $ADAFRUIT_BOOTLOADER_COMMIT, both in toolchain.env), cloned into
# firmware/build/bootloader with its submodules; the board definition is
# firmware/bootloader/urchin_pp. It compiles with the Zephyr SDK's arm-zephyr-eabi GCC from
# ZMK's build image ($ZMK_BUILD_IMAGE), so the firmware and the bootloader share one pinned
# toolchain. Without that SDK on this machine, the script re-runs itself in the image.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/firmware/build/out}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
. "$ROOT/toolchain.env"

GCC="$(ls -d /opt/zephyr-sdk-*/arm-zephyr-eabi/bin 2>/dev/null | head -1 || true)"
if [ -z "$GCC" ]; then
  command -v docker >/dev/null 2>&1 || { echo "build_bootloader.sh: needs ZMK's build image or docker" >&2; exit 1; }
  mkdir -p "$OUT"  # mounted too, so an output directory outside the repo gets the files
  exec docker run --rm -v "$ROOT:$ROOT" -v "$OUT:$OUT" -w "$ROOT" "$ZMK_BUILD_IMAGE" \
    bash "$ROOT/scripts/firmware/build_bootloader.sh" "$OUT"
fi

WORK="$ROOT/firmware/build/bootloader"
rm -rf "$WORK"
git -c advice.detachedHead=false clone -q --depth 1 --branch "$ADAFRUIT_BOOTLOADER_VERSION" --recurse-submodules --shallow-submodules \
  https://github.com/adafruit/Adafruit_nRF52_Bootloader.git "$WORK"
have="$(git -C "$WORK" rev-parse HEAD)"
[ "$have" = "$ADAFRUIT_BOOTLOADER_COMMIT" ] || {
  echo "build_bootloader.sh: tag $ADAFRUIT_BOOTLOADER_VERSION is $have, toolchain.env pins $ADAFRUIT_BOOTLOADER_COMMIT" >&2
  exit 1
}
cp -R "$ROOT/firmware/bootloader/urchin_pp" "$WORK/src/boards/urchin_pp"

# intelhex (hex merging) from its pure-Python wheel, checksum-verified; Python imports from a wheel on its path
WHEEL="$WORK/intelhex-$INTELHEX_VERSION-py2.py3-none-any.whl"
python3 - "$WHEEL" "$INTELHEX_SHA256" <<'PY'
import hashlib, sys, urllib.request
path, want = sys.argv[1], sys.argv[2]
url = "https://files.pythonhosted.org/packages/py2.py3/i/intelhex/" + path.rsplit("/", 1)[1]
data = urllib.request.urlopen(url, timeout=60).read()
have = hashlib.sha256(data).hexdigest()
if have != want:
    sys.exit("build_bootloader.sh: %s has SHA-256 %s, toolchain.env pins %s" % (url, have, want))
open(path, "wb").write(data)
PY
export PYTHONPATH="$WHEEL${PYTHONPATH:+:$PYTHONPATH}"

# The bootloader puts __DATE__/__TIME__ into its USB drive's file dates; with SOURCE_DATE_EPOCH
# (GCC honours it) they are the pinned commit's date, so the build is reproducible.
export SOURCE_DATE_EPOCH="$(git -C "$WORK" log -1 --format=%ct)"

# NRFUTIL=true: skip the DFU-over-serial .zip, which needs adafruit-nrfutil and isn't used here
make -C "$WORK" BOARD=urchin_pp CROSS_COMPILE="$GCC/arm-zephyr-eabi-" PYTHON=python3 NRFUTIL=true all

mkdir -p "$OUT"
cp "$WORK"/_build/build-urchin_pp/urchin_pp_bootloader-*_s140_6.1.1.hex \
   "$WORK"/_build/build-urchin_pp/update-urchin_pp_bootloader-*_nosd.uf2 "$OUT/"
ls -la "$OUT"
