"""
BLE LE Advertisement — makes the Pi discoverable as "Pi Mouse".

Appearance 0x03C2 = 962 (HID Mouse).
"""

from __future__ import annotations
import dbus
import dbus.service

from .hid_descriptor import HID_SVC

DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
LE_ADVERT_IFACE = "org.bluez.LEAdvertisement1"
ADAPTER_PATH = "/org/bluez/hci0"

APPEARANCE_HID_MOUSE = 962

DEVICE_NAME = "PiMouse v2"  # Changed to force macOS cache invalidate

# Include both HID and Device Information Service UUIDs in advertisement
DIS_SVC = "0000180a-0000-1000-8000-00805f9b34fb"


class Advertisement(dbus.service.Object):
    def __init__(self, bus):
        self.path = ADAPTER_PATH + "/advertisement1"
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface == LE_ADVERT_IFACE:
            return {
                "Type": "peripheral",
                "ServiceUUIDs": dbus.Array([HID_SVC, DIS_SVC], signature="s"),
                "LocalName": DEVICE_NAME,
                "Appearance": dbus.UInt16(APPEARANCE_HID_MOUSE),
                "Discoverable": dbus.Boolean(True),
            }
        return {}

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.GetAll(interface).get(prop)

    @dbus.service.method(LE_ADVERT_IFACE)
    def Release(self):
        print("[!] Mouse advertisement released", flush=True)
