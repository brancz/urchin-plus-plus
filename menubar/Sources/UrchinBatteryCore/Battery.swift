// How ZMK lays out battery levels over GATT, and the text the menu bar shows for them.
//
// With CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_PROXY (firmware/config/urchin_pp_left.conf)
// the left half, ZMK's split central, exposes two Battery Services (0x180F):
//
//   - Zephyr's own: one Battery Level (0x2A19) whose Characteristic Presentation Format
//     (0x2904) has description 0x0106 "main". That is the left half's level.
//   - ZMK's proxy (app/src/split/bluetooth/central_bas_proxy.c): one Battery Level per
//     peripheral, each with description 0x0108 "auxiliary" and a User Description (0x2901)
//     "Peripheral <index>". Peripheral 0 is the right half. ZMK reports 0 for a peripheral
//     until it has a reading and again whenever the peripheral disconnects.

import Foundation

public enum BatterySource: Hashable, Comparable, Sendable {
    case central
    case peripheral(Int)

    public static func < (a: BatterySource, b: BatterySource) -> Bool {
        switch (a, b) {
        case (.central, .peripheral): return true
        case let (.peripheral(x), .peripheral(y)): return x < y
        default: return false
        }
    }

    /// urchin++'s names: the central is the left half, peripheral 0 the right.
    public var shortName: String {
        switch self {
        case .central: return "L"
        case .peripheral(0): return "R"
        case let .peripheral(n): return "P\(n)"
        }
    }

    public var name: String {
        switch self {
        case .central: return "Left half"
        case .peripheral(0): return "Right half"
        case let .peripheral(n): return "Peripheral \(n)"
        }
    }
}

public enum GATT {
    public static let batteryService = "180F"
    public static let batteryLevel = "2A19"
    public static let presentationFormat = "2904"
    public static let userDescription = "2901"
    /// GATT Namespace Descriptions (Bluetooth Assigned Numbers).
    public static let descriptionMain: UInt16 = 0x0106
    public static let descriptionAuxiliary: UInt16 = 0x0108
}

/// The description field of a Characteristic Presentation Format value: format (1 byte),
/// exponent (1), unit (2), namespace (1), description (2), little-endian.
public func presentationDescription(_ format: Data?) -> UInt16? {
    guard let format, format.count >= 7 else { return nil }
    let bytes = [UInt8](format)
    return UInt16(bytes[5]) | UInt16(bytes[6]) << 8
}

/// Which half a Battery Level characteristic belongs to, from its descriptors. Returns nil for
/// an auxiliary level that doesn't say which peripheral it is.
public func classify(presentationFormat: Data?, userDescription: String?) -> BatterySource? {
    if let userDescription {
        let words = userDescription.split(separator: " ")
        if words.count == 2, words[0] == "Peripheral", let index = Int(words[1]), index >= 0 {
            return .peripheral(index)
        }
    }
    if presentationDescription(presentationFormat) == GATT.descriptionAuxiliary {
        return nil
    }
    return .central
}

/// A Battery Level value: one byte, 0-100 %.
public func batteryLevel(_ value: Data?) -> UInt8? {
    guard let value, let level = value.first, level <= 100 else { return nil }
    return level
}

public struct Reading: Equatable, Sendable {
    public let source: BatterySource
    /// nil: no reading (a peripheral that reports 0).
    public let level: UInt8?

    public init(source: BatterySource, level: UInt8?) {
        self.source = source
        self.level = level
    }

    public static let lowLevel: UInt8 = 15

    public var isLow: Bool { level.map { $0 <= Reading.lowLevel } ?? false }

    /// For the menu bar: "L 85%", "R –".
    public var shortText: String {
        "\(source.shortName) " + (level.map { "\($0)%" } ?? "–")
    }

    /// For the menu: "Right half: 72%".
    public var longText: String {
        if let level { return "\(source.name): \(level)%" }
        return "\(source.name): no reading (asleep, or not connected to the left half)"
    }
}

/// The readings to show, central first. A peripheral's 0 means ZMK has no reading for it.
public func readings(_ levels: [BatterySource: UInt8]) -> [Reading] {
    levels.keys.sorted().map { source in
        let level = levels[source]!
        if case .peripheral = source, level == 0 {
            return Reading(source: source, level: nil)
        }
        return Reading(source: source, level: level)
    }
}
