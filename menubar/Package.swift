// swift-tools-version: 6.0
// urchin++ battery: a macOS menu-bar app showing both halves' battery levels (menubar/README.md).
// Built by scripts/menubar/build.sh with the Swift pinned in toolchain.env.
import PackageDescription

let package = Package(
    name: "UrchinBattery",
    platforms: [.macOS(.v14)],
    targets: [
        // GATT decoding and display text, without CoreBluetooth or AppKit, so it can be unit-tested.
        .target(name: "UrchinBatteryCore"),
        .executableTarget(name: "UrchinBattery", dependencies: ["UrchinBatteryCore"]),
        .testTarget(name: "UrchinBatteryCoreTests", dependencies: ["UrchinBatteryCore"]),
    ]
)
