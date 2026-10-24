# urchin++ Battery

A macOS menu-bar app that shows the battery level of both halves: `L 85%  R 72%`. A level of 15 % or less turns red. The menu has:

- the keyboard's connection state and each half's level;
- the last levels seen, while the keyboard is asleep or away;
- Refresh, Copy Diagnostics, Open at Login and Quit.

macOS shows only the left half's level, in its Bluetooth menu and settings. The left half reports both, though. ZMK's battery proxy (`firmware/config/urchin_pp_left.conf`) offers the right half's level as a second Battery Service, and this app reads both services.

## Build and install

Needs Apple's Command Line Tools at the version `toolchain.env` pins (`XCODE_VERSION`, `SWIFT_VERSION`). Xcode isn't needed.

```bash
scripts/menubar/build.sh                       # unit tests, then menubar/.build/out/urchin++ Battery.app
cp -R "menubar/.build/out/urchin++ Battery.app" /Applications/
open "/Applications/urchin++ Battery.app"
```

- **Bluetooth permission:** macOS asks for it on the first start. If you denied it, allow it in System Settings › Privacy & Security › Bluetooth.
- **Ad-hoc signing:** the app is signed ad-hoc, not with a developer certificate. It runs on the Mac that built it, but each rebuild is a new app to macOS, which asks for the Bluetooth permission again.
- **The CI artifact (`menubar`):** the same app, built by CI. A downloaded copy is quarantined, and macOS refuses to open it. Building locally avoids that. Otherwise, allow it under System Settings › Privacy & Security › Open Anyway, or run `xattr -dr com.apple.quarantine "urchin++ Battery.app"`.
- **Other ZMK keyboards:** the app looks for a connected keyboard named `urchin++`. To use it with another ZMK split keyboard whose central has the battery proxy enabled, set its name and restart the app:

  ```bash
  defaults write io.github.brancz.urchin-pp.battery KeyboardName "Urchin"
  ```

## How it works

macOS connects the keyboard itself, as a Bluetooth keyboard. The app never pairs or connects on its own. It asks CoreBluetooth for the devices macOS already has connected and that offer a Battery Service (0x180F), and it takes the one with the keyboard's name. Then it reads every Battery Level (0x2A19) on it and subscribes to changes. It tells the halves apart by each level's descriptors:

| Battery Level | Presentation format (0x2904) description | User description (0x2901) | Shown as |
|---|---|---|---|
| Zephyr's Battery Service | 0x0106 "main" | — | L (left half, ZMK's split central) |
| ZMK's proxy service | 0x0108 "auxiliary" | `Peripheral 0` | R (right half) |

ZMK reports a peripheral's level as 0 until it has a reading, and again when the peripheral disconnects. The app therefore shows `R –` ("no reading") for a 0 from the right half. That happens:

- while the right half sleeps or is away from the left;
- for a right half that is truly empty.

ZMK notifies a change of either level. The app also re-reads both levels every 5 minutes. CoreBluetooth has no event for a device that macOS connects later, so while the keyboard is absent the app looks for it every 30 seconds.

The decoding and labelling (`Sources/UrchinBatteryCore`) have unit tests, run with `swift test` by the build script. The Bluetooth and menu code (`Sources/UrchinBattery`) can only be checked against the real keyboard; that is part of bring-up.

## Troubleshooting

- **Only `L` shows, and the menu says the right half isn't reported:** the left half's firmware has no battery proxy. This repo's firmware has it. If you added it to an already paired keyboard, macOS may still have the old service list cached: remove the keyboard in System Settings › Bluetooth and pair it again.
- **Nothing shows:** check that the keyboard is paired with this Mac and connected over Bluetooth (System Settings › Bluetooth). Then use Copy Diagnostics: it puts the app's view on the clipboard. That includes the name the app looks for, the names of all connected devices that offer a Battery Service, and every Battery Level found on the keyboard.
