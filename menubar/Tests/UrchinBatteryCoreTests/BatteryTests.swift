import Foundation
import Testing
import UrchinBatteryCore

// Characteristic Presentation Format values as ZMK and Zephyr send them: uint8 (0x04),
// exponent 0, unit 0x27AD (percentage), namespace 0x01 (Bluetooth SIG), description.
let mainFormat = Data([0x04, 0x00, 0xAD, 0x27, 0x01, 0x06, 0x01])
let auxiliaryFormat = Data([0x04, 0x00, 0xAD, 0x27, 0x01, 0x08, 0x01])

@Test func zephyrBatteryLevelIsTheLeftHalf() {
    #expect(presentationDescription(mainFormat) == 0x0106)
    #expect(classify(presentationFormat: mainFormat, userDescription: nil) == .central)
}

@Test func zmkProxyLevelIsThePeripheralItNames() {
    #expect(presentationDescription(auxiliaryFormat) == 0x0108)
    #expect(classify(presentationFormat: auxiliaryFormat, userDescription: "Peripheral 0") == .peripheral(0))
    #expect(classify(presentationFormat: auxiliaryFormat, userDescription: "Peripheral 2") == .peripheral(2))
}

@Test func auxiliaryLevelWithoutAPeripheralIndexIsSkipped() {
    #expect(classify(presentationFormat: auxiliaryFormat, userDescription: nil) == nil)
    #expect(classify(presentationFormat: auxiliaryFormat, userDescription: "Peripheral") == nil)
    #expect(classify(presentationFormat: auxiliaryFormat, userDescription: "Peripheral -1") == nil)
}

@Test func levelWithoutDescriptorsIsTheCentral() {
    // Older Zephyr releases had no presentation format on the Battery Level.
    #expect(classify(presentationFormat: nil, userDescription: nil) == .central)
    #expect(classify(presentationFormat: Data([0x04, 0x00]), userDescription: nil) == .central)
}

@Test func batteryLevelIsOneByteUpTo100() {
    #expect(batteryLevel(Data([85])) == 85)
    #expect(batteryLevel(Data([100, 7])) == 100)
    #expect(batteryLevel(Data([101])) == nil)
    #expect(batteryLevel(Data()) == nil)
    #expect(batteryLevel(nil) == nil)
}

@Test func readingsPutTheLeftHalfFirst() {
    let shown = readings([.peripheral(0): 72, .central: 85])
    #expect(shown.map(\.shortText) == ["L 85%", "R 72%"])
    #expect(shown.map(\.longText) == ["Left half: 85%", "Right half: 72%"])
}

@Test func peripheralZeroMeansNoReading() {
    let shown = readings([.central: 0, .peripheral(0): 0])
    #expect(shown == [Reading(source: .central, level: 0), Reading(source: .peripheral(0), level: nil)])
    #expect(shown.map(\.shortText) == ["L 0%", "R –"])
    #expect(!shown[1].isLow)
}

@Test func lowLevels() {
    #expect(Reading(source: .central, level: 15).isLow)
    #expect(!Reading(source: .central, level: 16).isLow)
}

@Test func sourcesSortCentralFirst() {
    #expect([BatterySource.peripheral(1), .central, .peripheral(0)].sorted() == [.central, .peripheral(0), .peripheral(1)])
}
