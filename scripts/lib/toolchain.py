"""Read the pinned tool versions from toolchain.env at the repo root."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path=ROOT / "toolchain.env"):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"')
    return values


def pinned(key):
    return load()[key]
