/*
 * Adafruit nRF52 bootloader: board definition for urchin++ (both halves).
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef _URCHIN_PP_H
#define _URCHIN_PP_H

// The module runs from VDDH (the charger's output), so VDD comes from REG0, whose
// default output is 1.8 V. The bootloader programs 3.3 V once (UICR), then resets.
#define UICR_REGOUT0_VALUE UICR_REGOUT0_VOUT_3V3

// No LED: one bootloader serves both halves, and each half's status-LED pins are key
// inputs on the other half, where driving them would short a pressed key's pin to ground.
#define LEDS_NUMBER 0

// No buttons: enter the bootloader by double-tapping reset (SW36), or with ZMK's
// &bootloader behavior. REG0's DC/DC stays off (no inductor), as does REG1's here.

//--------------------------------------------------------------------+
// BLE OTA
//--------------------------------------------------------------------+
#define BLEDIS_MANUFACTURER "urchin++"
#define BLEDIS_MODEL        "urchin++"

//--------------------------------------------------------------------+
// USB
// pid.codes test VID/PID 1209:0001. It is not universally unique and must not be used
// outside a test environment: fine for this private, non-distributed keyboard only
// (https://pid.codes/1209/0001/).
//--------------------------------------------------------------------+
#define USB_DESC_VID          0x1209
#define USB_DESC_UF2_PID      0x0001
#define USB_DESC_CDC_ONLY_PID 0x0001

#define UF2_PRODUCT_NAME      "urchin++"
#define UF2_VOLUME_LABEL      "URCHINPP"
#define UF2_BOARD_ID          "nRF52840-urchinpp"
#define UF2_INDEX_URL         "https://github.com/brancz/urchin-plus-plus"

#endif // _URCHIN_PP_H
