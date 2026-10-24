#!/usr/bin/env bash
# urchin++ Battery, the macOS menu-bar app that shows both halves' battery levels (menubar/).
#
#   scripts/menubar/build.sh [OUT_DIR]     default menubar/.build/out
#
#   OUT_DIR/urchin++ Battery.app       ad-hoc signed, arm64; copy it to /Applications
#   OUT_DIR/urchin++ Battery.app.zip   the same, zipped for CI artifacts
#
# Runs the unit tests, then builds with the Swift that toolchain.env pins: Apple's Command
# Line Tools $XCODE_VERSION locally, Xcode $XCODE_VERSION in CI. Xcode itself isn't needed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/menubar/.build/out}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
. "$ROOT/toolchain.env"

have="$(swift --version 2>&1 | sed -n 's/.*Apple Swift version \([0-9.]*\).*/\1/p' | head -1)"
[ "$have" = "$SWIFT_VERSION" ] || {
  echo "menubar/build.sh: need Swift $SWIFT_VERSION (Xcode or Command Line Tools $XCODE_VERSION), got ${have:-none}" >&2
  exit 1
}

cd "$ROOT/menubar"
# Xcode finds the Testing framework by itself; the Command Line Tools need its paths given.
DEV="$(xcode-select -p)"
case "$DEV" in
  */CommandLineTools)
    L="$DEV/Library/Developer"
    swift test -Xswiftc -F -Xswiftc "$L/Frameworks" \
      -Xlinker -rpath -Xlinker "$L/Frameworks" -Xlinker -rpath -Xlinker "$L/usr/lib" ;;
  *) swift test ;;
esac
swift build -c release --product UrchinBattery
BIN="$(swift build -c release --show-bin-path)/UrchinBattery"

APP="$OUT/urchin++ Battery.app"
rm -rf "$APP" "$APP.zip"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN" "$APP/Contents/MacOS/UrchinBattery"
cp Info.plist "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist" >/dev/null
# Ad-hoc signature: enough to run on the Mac that built it, and for macOS to remember the
# Bluetooth permission for this build (docs: menubar/README.md).
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict "$APP"
(cd "$OUT" && ditto -c -k --keepParent "urchin++ Battery.app" "urchin++ Battery.app.zip")
echo "built $APP"
