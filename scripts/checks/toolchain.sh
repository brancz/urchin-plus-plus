#!/usr/bin/env bash
# Verify the installed tools match toolchain.env exactly (CLAUDE.md rule 4).
#
#   scripts/checks/toolchain.sh          # tools every build needs (CI and local)
#   scripts/checks/toolchain.sh --local  # plus easyeda2kicad and pyOCD (workstation only)
#   scripts/checks/toolchain.sh --kicad  # only kicad-cli and pcbnew (fast preflight for other scripts)
#
# Needs KICAD_PY and FREEROUTING_JAR set as in docs/SETUP.md.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
set -a
# shellcheck disable=SC1091
. "$ROOT/toolchain.env"
set +a

fails=0
check() {  # name, expected, actual
  if [ "$2" = "$3" ]; then
    printf 'ok   %-16s %s\n' "$1" "$3"
  else
    printf 'FAIL %-16s expected %s, got %s\n' "$1" "$2" "${3:-<missing>}"
    fails=$((fails + 1))
  fi
}
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
pyver() { "${KICAD_PY:-python3}" -c "$1" 2>/dev/null | tail -1; }

check kicad-cli "$KICAD_VERSION" "$(kicad-cli version 2>/dev/null)"
check pcbnew "$KICAD_VERSION" "$(pyver 'import pcbnew; print(pcbnew.Version())')"
if [ "${1:-}" = "--kicad" ]; then
  [ "$fails" -eq 0 ] || { echo "toolchain: KiCad on PATH/KICAD_PY is not $KICAD_VERSION (see docs/SETUP.md)"; exit 1; }
  exit 0
fi
check kikit "$KIKIT_VERSION" "$(pyver 'import kikit; print(kikit.__version__)')"
check atopile "$ATOPILE_VERSION" "$(ato --version 2>/dev/null | tail -1)"
check freerouting.jar "$FREEROUTING_SHA256" "$(sha256 "${FREEROUTING_JAR:-/nonexistent}" 2>/dev/null)"
java_major="$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1)"
if [ -n "$java_major" ] && [ "$java_major" -ge "$JAVA_MIN_MAJOR" ]; then
  printf 'ok   %-16s %s (>= %s)\n' java "$java_major" "$JAVA_MIN_MAJOR"
else
  printf 'FAIL %-16s need >= %s, got %s\n' java "$JAVA_MIN_MAJOR" "${java_major:-<missing>}"
  fails=$((fails + 1))
fi

if [ "${1:-}" = "--local" ]; then
  check easyeda2kicad "$EASYEDA2KICAD_VERSION" "$(easyeda2kicad --version 2>/dev/null | sed -n 's/.*v\([0-9.]*\).*/\1/p')"
  check pyocd "$PYOCD_VERSION" "$(pyocd --version 2>/dev/null)"
  if "$ROOT/scripts/freeze_constraints.sh" --check >/dev/null 2>&1; then
    printf 'ok   %-16s %s\n' constraints "atopile and KiKit trees match constraints/"
  else
    printf 'FAIL %-16s %s\n' constraints "installed trees differ from constraints/ (scripts/freeze_constraints.sh --check)"
    fails=$((fails + 1))
  fi
fi

if grep -q "image: $KICAD_IMAGE\$" "$ROOT/.github/workflows/ci.yml"; then
  printf 'ok   %-16s %s\n' ci-image "$KICAD_IMAGE"
else
  printf 'FAIL %-16s .github/workflows/ci.yml does not use %s\n' ci-image "$KICAD_IMAGE"
  fails=$((fails + 1))
fi

if grep -q "image: $ZMK_BUILD_IMAGE\$" "$ROOT/.github/workflows/ci.yml"; then
  printf 'ok   %-16s %s\n' zmk-image "$ZMK_BUILD_IMAGE"
else
  printf 'FAIL %-16s .github/workflows/ci.yml does not use %s\n' zmk-image "$ZMK_BUILD_IMAGE"
  fails=$((fails + 1))
fi

[ "$fails" -eq 0 ] || { echo "toolchain: $fails mismatch(es)"; exit 1; }
echo "toolchain: OK"
