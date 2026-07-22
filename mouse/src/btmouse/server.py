"""
BLE HID Mouse server — wires all modules together.

Uses the EXACT same structure as keyboard that works.
"""

from __future__ import annotations
import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from .gatt import Application, HIDMouseService, DeviceInformationService, get_report_char
from .advertisement import Advertisement, ADAPTER_PATH, DEVICE_NAME
from .agent import PairingAgent, AGENT_PATH, AGENT_MGR_IFACE
from .command_socket import MouseCommandSocket, SOCKET_PATH

BLUEZ = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERT_MGR_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"


def handle_reports(reports: list[dict]):
    """Send mouse reports as BLE HID notifications."""
    import time
    char = get_report_char()
    if not char:
        print("[!] No client subscribed — host not connected", flush=True)
        return 0
    for r in reports:
        byte_report = [
            r["buttons"] & 0x07,
            r["x"] & 0xFF,
            r["y"] & 0xFF,
            r["wheel"] & 0xFF,
        ]
        char.send_notification(byte_report)
        time.sleep(0.02)
    print(f"[+] Sent {len(reports)} mouse reports", flush=True)
    return len(reports)


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # ── 1. Pairing agent ──
    agent = PairingAgent(bus)
    agent_mgr = dbus.Interface(bus.get_object(BLUEZ, "/org/bluez"), AGENT_MGR_IFACE)
    agent_mgr.RegisterAgent(
        AGENT_PATH,
        "KeyboardDisplay",
        reply_handler=lambda: print("[+] Agent registered", flush=True),
        error_handler=lambda e: print("[!] Agent error: " + str(e), flush=True),
    )
    agent_mgr.RequestDefaultAgent(
        AGENT_PATH,
        reply_handler=lambda: print("[+] Default agent", flush=True),
        error_handler=lambda e: print("[!] Default agent error: " + str(e), flush=True),
    )

    # ── 2. GATT service ──
    app = Application(bus)
    app.add_service(HIDMouseService(bus, 0))
    app.add_service(DeviceInformationService(bus, 1))

    gatt_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), GATT_MANAGER_IFACE)

    def gatt_ok():
        print("[+] GATT registered", flush=True)

    def gatt_err(e):
        print("[!] GATT FAILED: " + str(e), flush=True)

    gatt_mgr.RegisterApplication(
        app.get_path(),
        {},
        reply_handler=gatt_ok,
        error_handler=gatt_err,
    )

    # ── 3. BLE advertisement ──
    ad = Advertisement(bus)
    ad_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), LE_ADVERT_MGR_IFACE)
    ad_mgr.RegisterAdvertisement(
        ad.get_path(),
        {},
        reply_handler=lambda: print("[+] Advertisement registered", flush=True),
        error_handler=lambda e: print("[!] Ad error: " + str(e), flush=True),
    )

    # ── 4. Adapter properties ──
    props = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), DBUS_PROP_IFACE)
    props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
    props.Set("org.bluez.Adapter1", "Alias", DEVICE_NAME)
    props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
    props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))

    # ── 5. Command socket ──
    MouseCommandSocket(handle_reports, SOCKET_PATH)

    # ── 6. Run ──
    print(f"[*] BLE HID Mouse (Boot Protocol) running", flush=True)
    print(f"[*] Pair as '{DEVICE_NAME}'", flush=True)
    print(f"[*] Commands: echo '{{\"cmd\":\"move\",\"dx\":10,\"dy\":0}}' | socat - UNIX-CONNECT:{SOCKET_PATH}", flush=True)
    try:
        GLib.MainLoop().run()
    except KeyboardInterrupt:
        print("\n[*] Shutting down", flush=True)


if __name__ == "__main__":
    main()