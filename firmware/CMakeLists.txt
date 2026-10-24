# SPDX-License-Identifier: MIT

if(CONFIG_URCHIN_BATTERY_POWER_AWARE)
  zephyr_library()
  zephyr_library_sources(drivers/battery_power_aware/battery_power_aware.c)
endif()
