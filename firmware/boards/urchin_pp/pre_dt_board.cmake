# SPDX-License-Identifier: MIT

# Suppresses duplicate unit-address warnings for power, clock, acl and flash-controller,
# as in ZMK's own nRF52840 boards.
list(APPEND EXTRA_DTC_FLAGS "-Wno-unique_unit_address_if_enabled")
