"""
BLE HID Keyboard server — wires all modules together.

Entry point that:
  1. Initializes D-Bus + BlueZ
  2. Registers the pairing agent
  3. Registers the GATT HID service
  4. Registers the BLE advertisement
  5. Starts the command socket
  6. Runs the GLib main loop

This is the direct modular equivalent of bt_keyboard_v5.py main().
"""

from __future__ import annotations
import os
import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from .gatt import Application, HIDService, get_report_char
from .advertisement import Advertisement, ADAPTER_PATH, DEVICE_NAME
from .agent import PairingAgent, AGENT_PATH, AGENT_MGR_IFACE
from .command_socket import CommandSocket, SOCKET_PATH
from .typing import type_text_sync

BLUEZ = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERT_MGR_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"


def type_text(text: str):
    """Type text on the connected iOS device via BLE HID notifications."""
    char = get_report_char()
    if not char:
        print("[!] No client subscribed — iOS not connected", flush=True)
        return 0
    count = type_text_sync(text, char.send_notification)
    print(f"[+] Typed {count} characters", flush=True)
    return count


def main():
    """Start the BLE HID keyboard server."""
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
    app.add_service(HIDService(bus, 0))

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
    cmd = CommandSocket(on_text_callback=type_text, socket_path=SOCKET_PATH)
    cmd.start()

    # ── 6. Run forever ──
    print("[*] BLE HID Keyboard (Boot Protocol) running", flush=True)
    print(f"[*] Pair as '{DEVICE_NAME}'", flush=True)
    print(f"[*] Type: echo hello | socat - UNIX-CONNECT:{SOCKET_PATH}", flush=True)

    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
