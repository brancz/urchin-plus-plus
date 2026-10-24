# SPDX-License-Identifier: MIT

# Flashing goes through the UF2 bootloader (double-tap reset); the one-time bootloader
# flash uses an SWD probe (docs: firmware/README.md).
include(${ZEPHYR_BASE}/boards/common/uf2.board.cmake)
