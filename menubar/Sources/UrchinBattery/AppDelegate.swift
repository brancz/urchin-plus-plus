// The status item: "L 85%  R 72%" in the menu bar, details and settings in its menu.

import AppKit
import ServiceManagement
import UrchinBatteryCore

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let monitor = BatteryMonitor(
        keyboardName: UserDefaults.standard.string(forKey: "KeyboardName") ?? "urchin++")

    func applicationDidFinishLaunching(_ notification: Notification) {
        let image = NSImage(systemSymbolName: "keyboard", accessibilityDescription: "Keyboard battery")
        image?.isTemplate = true
        statusItem.button?.image = image
        statusItem.button?.imagePosition = .imageLeading
        let menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu
        monitor.onChange = { [weak self] in self?.renderTitle() }
        monitor.start()
        renderTitle()
    }

    private func renderTitle() {
        let shown = readings(monitor.levels)
        guard let button = statusItem.button else { return }
        if shown.isEmpty {
            button.attributedTitle = NSAttributedString(string: "")
            button.toolTip = statusText
            return
        }
        let title = NSMutableAttributedString()
        let font = NSFont.monospacedDigitSystemFont(ofSize: NSFont.systemFontSize, weight: .regular)
        for (i, reading) in shown.enumerated() {
            var attributes: [NSAttributedString.Key: Any] = [.font: font]
            if reading.isLow { attributes[.foregroundColor] = NSColor.systemRed }
            title.append(NSAttributedString(string: (i == 0 ? " " : "  ") + reading.shortText, attributes: attributes))
        }
        button.attributedTitle = title
        button.toolTip = shown.map(\.longText).joined(separator: "\n")
    }

    private var statusText: String {
        let name = monitor.keyboardName
        switch monitor.status {
        case .starting: return "Starting…"
        case .bluetoothOff: return "Bluetooth is off"
        case .unauthorized: return "No Bluetooth access: allow it in System Settings › Privacy & Security › Bluetooth"
        case .unsupported: return "This Mac has no Bluetooth LE"
        case .notConnected: return "\(name) is not connected"
        case .connecting: return "Connecting to \(name)…"
        case .connected: return name
        }
    }

    // Rebuilt every time the menu opens, so it never shows stale text.
    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        menu.addItem(disabled(statusText))
        let shown = readings(monitor.levels)
        if !shown.isEmpty {
            for reading in shown { menu.addItem(disabled(reading.longText)) }
            if !shown.contains(where: { $0.source != .central }) {
                menu.addItem(disabled("Right half: not reported (enable ZMK's battery proxy on the left half)"))
            }
        } else if monitor.status != .connected, let last = monitor.lastSeen {
            let time = last.at.formatted(date: .omitted, time: .shortened)
            let levels = readings(last.levels).map(\.shortText).joined(separator: "  ")
            menu.addItem(disabled("Last seen at \(time): \(levels)"))
        }
        menu.addItem(.separator())
        menu.addItem(item("Refresh", #selector(refresh), "r"))
        menu.addItem(item("Copy Diagnostics", #selector(copyDiagnostics), ""))
        let login = item("Open at Login", #selector(toggleLogin), "")
        login.state = SMAppService.mainApp.status == .enabled ? .on : .off
        menu.addItem(login)
        menu.addItem(.separator())
        menu.addItem(item("Quit", #selector(NSApplication.terminate(_:)), "q", target: NSApp))
    }

    private func disabled(_ title: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        item.isEnabled = false
        return item
    }

    private func item(_ title: String, _ action: Selector, _ key: String, target: AnyObject? = nil) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = target ?? self
        return item
    }

    @objc private func refresh() {
        monitor.refresh()
    }

    @objc private func copyDiagnostics() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(monitor.diagnostics(), forType: .string)
    }

    @objc private func toggleLogin() {
        do {
            if SMAppService.mainApp.status == .enabled {
                try SMAppService.mainApp.unregister()
            } else {
                try SMAppService.mainApp.register()
            }
        } catch {
            let alert = NSAlert(error: error)
            alert.runModal()
        }
    }
}
