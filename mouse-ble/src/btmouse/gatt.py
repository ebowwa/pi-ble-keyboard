"""
BlueZ GATT server — D-Bus objects for the HID Mouse service.

Same structure as the keyboard GATT but with mouse HID descriptor and
4-byte mouse reports.
"""

from __future__ import annotations
import dbus
import dbus.service

from .hid_descriptor import (
    HID_SVC,
    HID_INFO_UUID,
    HID_REPORT_MAP_UUID,
    HID_CTRL_UUID,
    HID_REPORT_UUID,
    HID_PROTO_UUID,
    REPORT_REF_UUID,
    MOUSE_REPORT_MAP,
    HID_INFORMATION,
    REPORT_REF_BOOT_MOUSE,
)

DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESC_IFACE = "org.bluez.GattDescriptor1"

_report_char = None


def get_report_char():
    return _report_char


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = "/"
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.get_characteristics():
                response[chrc.get_path()] = chrc.get_properties()
                for desc in chrc.get_descriptors():
                    response[desc.get_path()] = desc.get_properties()
        return response


class Service(dbus.service.Object):
    PATH_PREFIX = "/pimouse"

    def __init__(self, bus, index, uuid, primary=True):
        self.path = self.PATH_PREFIX + "/service" + str(index)
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, char):
        self.characteristics.append(char)

    def get_properties(self):
        return {GATT_SERVICE_IFACE: {"UUID": self.uuid, "Primary": self.primary}}

    def get_characteristics(self):
        return self.characteristics


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + "/char" + str(index)
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.value = [0]
        self.notifying = False
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, desc):
        self.descriptors.append(desc)

    def get_descriptors(self):
        return self.descriptors

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                "Service": self.service.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        props = self.get_properties()
        if interface in props:
            return props[interface]
        return {}

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        return dbus.Array(self.value, signature="y")

    @dbus.service.method(GATT_CHRC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        self.value = list(value)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False

    @dbus.service.signal(DBUS_PROP_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def send_notification(self, value):
        self.value = list(value)
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {"Value": dbus.Array(self.value, signature="y")},
            [],
        )


class Descriptor(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, characteristic):
        self.path = characteristic.path + "/desc" + str(index)
        self.uuid = uuid
        self.flags = flags
        self.characteristic = characteristic
        self.value = [0]
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_DESC_IFACE: {
                "Characteristic": self.characteristic.get_path(),
                "UUID": self.uuid,
                "Flags": self.flags,
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        props = self.get_properties()
        if interface in props:
            return props[interface]
        return {}

    @dbus.service.method(GATT_DESC_IFACE, in_signature="a{sv}", out_signature="ay")
    def ReadValue(self, options):
        return dbus.Array(self.value, signature="y")

    @dbus.service.method(GATT_DESC_IFACE, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        self.value = list(value)


# ── HID Mouse characteristics ──


class HIDInfoChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_INFO_UUID, ["read"], service)
        self.value = HID_INFORMATION


class HIDReportMapChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_REPORT_MAP_UUID, ["read"], service)
        self.value = MOUSE_REPORT_MAP


class HIDReportChar(Characteristic):
    """HID Report — 4-byte mouse reports, notify-enabled."""

    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_REPORT_UUID, ["read", "notify"], service)
        self.value = [0] * 4  # 4 bytes, NO Report ID prefix

    def StartNotify(self):
        super().StartNotify()
        global _report_char
        _report_char = self
        print("[+] Mouse notifications ENABLED", flush=True)

    def StopNotify(self):
        super().StopNotify()
        global _report_char
        _report_char = None


class HIDProtocolModeChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_PROTO_UUID, ["read", "write-without-response"], service)
        self.value = [0x01]  # Report Protocol Mode


class HIDCtrlPointChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_CTRL_UUID, ["write-without-response"], service)


class ReportReferenceDesc(Descriptor):
    def __init__(self, bus, index, characteristic):
        super().__init__(bus, index, REPORT_REF_UUID, ["read"], characteristic)
        self.value = REPORT_REF_BOOT_MOUSE


class HIDMouseService(Service):
    def __init__(self, bus, index):
        super().__init__(bus, index, HID_SVC, True)
        self.add_characteristic(HIDInfoChar(bus, 0, self))
        self.add_characteristic(HIDReportMapChar(bus, 1, self))
        report = HIDReportChar(bus, 2, self)
        report.add_descriptor(ReportReferenceDesc(bus, 0, report))
        self.add_characteristic(report)
        self.add_characteristic(HIDProtocolModeChar(bus, 3, self))
        self.add_characteristic(HIDCtrlPointChar(bus, 4, self))
