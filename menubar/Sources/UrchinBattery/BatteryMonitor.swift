// Finds the keyboard among the Bluetooth devices macOS has connected, and reads and subscribes
// to every Battery Level it exposes (UrchinBatteryCore/Battery.swift has the GATT layout).
//
// macOS connects the keyboard itself, as a HID device. retrieveConnectedPeripherals returns
// such system-connected devices, and connect() adds this app as one more user of that
// connection; it never pairs or connects on its own. CoreBluetooth has no callback for a
// device that macOS connects later, so while the keyboard is absent the app polls.

import CoreBluetooth
import Foundation
import UrchinBatteryCore

@MainActor
final class BatteryMonitor: NSObject {
    enum Status {
        case starting, bluetoothOff, unauthorized, unsupported, notConnected, connecting, connected
    }

    private static let pollInterval: TimeInterval = 30   // looking for the keyboard
    private static let refreshInterval: TimeInterval = 300 // re-reading, besides notifications

    let keyboardName: String
    private(set) var status = Status.starting
    /// The latest level per half, while connected.
    private(set) var levels: [BatterySource: UInt8] = [:]
    /// The last levels seen, kept after the keyboard disconnects or sleeps.
    private(set) var lastSeen: (levels: [BatterySource: UInt8], at: Date)?
    var onChange: (() -> Void)?

    private var manager: CBCentralManager!
    private var keyboard: CBPeripheral?
    private var timer: Timer?
    private var lastRead = Date.distantPast

    /// Per Battery Level characteristic: what its descriptors and value say so far.
    private struct Level {
        let characteristic: CBCharacteristic
        var descriptorsKnown = false
        var pendingReads = 0
        var presentationFormat: Data?
        var userDescription: String?
        var value: Data?
    }
    private var tracked: [ObjectIdentifier: Level] = [:]

    init(keyboardName: String) {
        self.keyboardName = keyboardName
        super.init()
    }

    func start() {
        manager = CBCentralManager(delegate: self, queue: nil)
        timer = Timer.scheduledTimer(withTimeInterval: Self.pollInterval, repeats: true) { _ in
            MainActor.assumeIsolated { self.tick() }
        }
    }

    /// Looks for the keyboard again, or re-reads its levels.
    func refresh() {
        if keyboard == nil {
            find()
        } else {
            readAll()
        }
    }

    private func tick() {
        if keyboard == nil {
            find()
        } else if Date().timeIntervalSince(lastRead) >= Self.refreshInterval {
            readAll()
        }
    }

    private func find() {
        guard manager.state == .poweredOn, keyboard == nil else { return }
        let connected = manager.retrieveConnectedPeripherals(withServices: [CBUUID(string: GATT.batteryService)])
        guard let found = connected.first(where: { $0.name == keyboardName }) else {
            setStatus(.notConnected)
            return
        }
        keyboard = found
        found.delegate = self
        setStatus(.connecting)
        manager.connect(found)
    }

    private func readAll() {
        guard let keyboard else { return }
        lastRead = Date()
        for level in tracked.values {
            keyboard.readValue(for: level.characteristic)
        }
    }

    private func forget() {
        if let keyboard, manager.state == .poweredOn { manager.cancelPeripheralConnection(keyboard) }
        keyboard = nil
        tracked = [:]
        levels = [:]
    }

    private func setStatus(_ new: Status) {
        status = new
        onChange?()
    }

    /// Recomputes `levels` from every characteristic whose descriptors and value are known.
    private func update() {
        var new: [BatterySource: UInt8] = [:]
        for level in tracked.values where level.descriptorsKnown && level.pendingReads == 0 {
            guard let source = classify(presentationFormat: level.presentationFormat,
                                        userDescription: level.userDescription),
                  let value = batteryLevel(level.value) else { continue }
            new[source] = value
        }
        levels = new
        if !new.isEmpty { lastSeen = (new, Date()) }
        onChange?()
    }

    /// The GATT layout as this app sees it, for bug reports and bring-up.
    func diagnostics() -> String {
        var lines = ["keyboard name: \(keyboardName)", "status: \(status)"]
        if manager.state == .poweredOn {
            let connected = manager.retrieveConnectedPeripherals(withServices: [CBUUID(string: GATT.batteryService)])
            lines.append("connected with a Battery Service: \(connected.map { $0.name ?? "?" })")
        }
        if let keyboard {
            lines.append("peripheral: \(keyboard.name ?? "?") \(keyboard.identifier.uuidString)")
            for service in keyboard.services ?? [] {
                lines.append("service \(service.uuid.uuidString)")
                for characteristic in service.characteristics ?? [] {
                    let level = tracked[ObjectIdentifier(characteristic)]
                    lines.append("  characteristic \(characteristic.uuid.uuidString) value \(hex(characteristic.value))")
                    for descriptor in characteristic.descriptors ?? [] {
                        lines.append("    descriptor \(descriptor.uuid.uuidString) \(String(describing: descriptor.value ?? "nil"))")
                    }
                    if let level {
                        let source = classify(presentationFormat: level.presentationFormat, userDescription: level.userDescription)
                        lines.append("    -> \(source.map { "\($0)" } ?? "unknown peripheral"), descriptors known: \(level.descriptorsKnown), pending reads: \(level.pendingReads)")
                    }
                }
            }
        }
        lines.append("levels: \(readings(levels).map(\.shortText).joined(separator: " "))")
        return lines.joined(separator: "\n")
    }
}

private func hex(_ data: Data?) -> String {
    data.map { $0.map { String(format: "%02x", $0) }.joined() } ?? "nil"
}

extension BatteryMonitor: @preconcurrency CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn:
            find()
        case .unauthorized:
            forget()
            setStatus(.unauthorized)
        case .unsupported:
            forget()
            setStatus(.unsupported)
        default:
            forget()
            setStatus(.bluetoothOff)
        }
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        guard peripheral == keyboard else { return }
        setStatus(.connected)
        peripheral.discoverServices([CBUUID(string: GATT.batteryService)])
    }

    func centralManager(_ central: CBCentralManager, didFailToConnect peripheral: CBPeripheral, error: Error?) {
        guard peripheral == keyboard else { return }
        forget()
        setStatus(.notConnected)
    }

    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        guard peripheral == keyboard else { return }
        forget()
        setStatus(.notConnected)
    }
}

extension BatteryMonitor: @preconcurrency CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        for service in peripheral.services ?? [] where service.uuid == CBUUID(string: GATT.batteryService) {
            peripheral.discoverCharacteristics([CBUUID(string: GATT.batteryLevel)], for: service)
        }
    }

    func peripheral(_ peripheral: CBPeripheral, didModifyServices invalidatedServices: [CBService]) {
        // New firmware (e.g. one that adds or drops the proxy service): start over.
        tracked = [:]
        update()
        peripheral.discoverServices([CBUUID(string: GATT.batteryService)])
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        for characteristic in service.characteristics ?? [] where characteristic.uuid == CBUUID(string: GATT.batteryLevel) {
            let id = ObjectIdentifier(characteristic)
            guard tracked[id] == nil else { continue }
            tracked[id] = Level(characteristic: characteristic)
            peripheral.discoverDescriptors(for: characteristic)
            if characteristic.properties.contains(.notify) {
                peripheral.setNotifyValue(true, for: characteristic)
            }
            peripheral.readValue(for: characteristic)
        }
        lastRead = Date()
    }

    func peripheral(_ peripheral: CBPeripheral, didDiscoverDescriptorsFor characteristic: CBCharacteristic, error: Error?) {
        let id = ObjectIdentifier(characteristic)
        guard tracked[id] != nil else { return }
        let wanted = [CBUUID(string: GATT.presentationFormat), CBUUID(string: GATT.userDescription)]
        for descriptor in characteristic.descriptors ?? [] where wanted.contains(descriptor.uuid) {
            tracked[id]!.pendingReads += 1
            peripheral.readValue(for: descriptor)
        }
        tracked[id]!.descriptorsKnown = true
        update()
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor descriptor: CBDescriptor, error: Error?) {
        guard let characteristic = descriptor.characteristic else { return }
        let id = ObjectIdentifier(characteristic)
        guard tracked[id] != nil else { return }
        tracked[id]!.pendingReads = max(0, tracked[id]!.pendingReads - 1)
        if error == nil {
            switch descriptor.uuid {
            case CBUUID(string: GATT.presentationFormat):
                tracked[id]!.presentationFormat = descriptor.value as? Data
            case CBUUID(string: GATT.userDescription):
                // CoreBluetooth decodes the User Description to a string; raw bytes are UTF-8.
                if let text = descriptor.value as? String {
                    tracked[id]!.userDescription = text
                } else if let data = descriptor.value as? Data {
                    tracked[id]!.userDescription = String(decoding: data, as: UTF8.self)
                }
            default:
                break
            }
        }
        update()
    }

    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        let id = ObjectIdentifier(characteristic)
        guard tracked[id] != nil, error == nil else { return }
        tracked[id]!.value = characteristic.value
        update()
    }
}
