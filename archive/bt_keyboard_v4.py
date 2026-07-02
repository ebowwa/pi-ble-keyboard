#!/usr/bin/env python3
"""
BLE HID Keyboard for Raspberry Pi 4B.
Based on the proven BlueZ example-gatt-server pattern.
"""
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

import socket
import os
import threading
import time

BLUEZ = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
GATT_DESC_IFACE = "org.bluez.GattDescriptor1"
LE_ADVERT_IFACE = "org.bluez.LEAdvertisement1"
AGENT_IFACE = "org.bluez.Agent1"
AGENT_MGR_IFACE = "org.bluez.AgentManager1"
ADAPTER_PATH = "/org/bluez/hci0"

HID_SVC = "00001812-0000-1000-8000-00805f9b34fb"
HID_INFO_UUID = "00002A4A-0000-1000-8000-00805f9b34fb"
HID_REPORT_MAP_UUID = "00002A4B-0000-1000-8000-00805f9b34fb"
HID_CTRL_UUID = "00002A4C-0000-1000-8000-00805f9b34fb"
HID_REPORT_UUID = "00002A4D-0000-1000-8000-00805f9b34fb"
HID_PROTO_UUID = "00002A4E-0000-1000-8000-00805f9b34fb"
REPORT_REF_UUID = "00002908-0000-1000-8000-00805f9b34fb"

HID_REPORT_MAP = [
    0x05, 0x01, 0x09, 0x06, 0xA1, 0x01,
    0x85, 0x01,
    0x05, 0x07, 0x19, 0xE0, 0x29, 0xE7,
    0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x08, 0x81, 0x02,
    0x95, 0x01, 0x75, 0x08, 0x81, 0x01,
    0x95, 0x05, 0x75, 0x01, 0x05, 0x08,
    0x19, 0x01, 0x29, 0x05, 0x91, 0x02,
    0x95, 0x01, 0x75, 0x03, 0x91, 0x01,
    0x95, 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65,
    0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81, 0x00,
    0xC0,
]

KEYMAP = {
    "a":4,"b":5,"c":6,"d":7,"e":8,"f":9,"g":10,"h":11,"i":12,"j":13,
    "k":14,"l":15,"m":16,"n":17,"o":18,"p":19,"q":20,"r":21,"s":22,
    "t":23,"u":24,"v":25,"w":26,"x":27,"y":28,"z":29,
    "1":30,"2":31,"3":32,"4":33,"5":34,"6":35,"7":36,"8":37,"9":38,"0":39,
    " ":44,"\n":40,"\t":43,"-":45,"=":46,"[":47,"]":48,"\\":49,
    ";":51,"'":52,"`":50,",":53,".":54,"/":55,
}
SHIFT_KEYMAP = {
    "A":4,"B":5,"C":6,"D":7,"E":8,"F":9,"G":10,"H":11,"I":12,"J":13,
    "K":14,"L":15,"M":16,"N":17,"O":18,"P":19,"Q":20,"R":21,"S":22,
    "T":23,"U":24,"V":25,"W":26,"X":27,"Y":28,"Z":29,
    "!":30,"@":31,"#":32,"$":33,"%":34,"^":35,"&":36,"*":37,"(":38,")":39,
    "_":45,"+":46,"{":47,"}":48,"|":49,":":51,'"':52,"~":50,"<":53,">":54,"?":55,
}

CMD_SOCKET = "/tmp/bt_keyboard.sock"
_report_char = None


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
    PATH_PREFIX = "/pihid"

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
        return {GATT_CHRC_IFACE: {
            "Service": self.service.get_path(),
            "UUID": self.uuid,
            "Flags": self.flags,
        }}

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
        return {GATT_DESC_IFACE: {
            "Characteristic": self.characteristic.get_path(),
            "UUID": self.uuid,
            "Flags": self.flags,
        }}

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


class HIDInfoChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_INFO_UUID, ["read"], service)
        self.value = [0x01, 0x01, 0x00, 0x03]


class HIDReportMapChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_REPORT_MAP_UUID, ["read"], service)
        self.value = HID_REPORT_MAP


class HIDReportChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_REPORT_UUID, ["read", "notify"], service)
        self.value = [0] * 9

    def StartNotify(self):
        super().StartNotify()
        global _report_char
        _report_char = self
        print("[+] Notifications ENABLED - keyboard ready", flush=True)

    def send_key(self, hid_code, modifier=0):
        self.send_notification([0x01, modifier, 0, hid_code, 0, 0, 0, 0, 0])
        time.sleep(0.04)
        self.send_notification([0x01, 0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.04)


class HIDProtocolModeChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_PROTO_UUID, ["read", "write-without-response"], service)
        self.value = [0x01]


class HIDCtrlPointChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_CTRL_UUID, ["write-without-response"], service)


class ReportReferenceDesc(Descriptor):
    def __init__(self, bus, index, characteristic):
        super().__init__(bus, index, REPORT_REF_UUID, ["read"], characteristic)
        self.value = [0x01, 0x01]


class HIDService(Service):
    def __init__(self, bus, index):
        super().__init__(bus, index, HID_SVC, True)
        self.add_characteristic(HIDInfoChar(bus, 0, self))
        self.add_characteristic(HIDReportMapChar(bus, 1, self))
        report = HIDReportChar(bus, 2, self)
        report.add_descriptor(ReportReferenceDesc(bus, 0, report))
        self.add_characteristic(report)
        self.add_characteristic(HIDProtocolModeChar(bus, 3, self))
        self.add_characteristic(HIDCtrlPointChar(bus, 4, self))


class Advertisement(dbus.service.Object):
    def __init__(self, bus):
        self.path = ADAPTER_PATH + "/advertisement0"
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface == LE_ADVERT_IFACE:
            return {
                "Type": "peripheral",
                "ServiceUUIDs": dbus.Array([HID_SVC], signature="s"),
                "LocalName": "Pi Keyboard",
                "Appearance": dbus.UInt16(961),
                "Discoverable": dbus.Boolean(True),
            }
        return {}

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        return self.GetAll(interface).get(prop)

    @dbus.service.method(LE_ADVERT_IFACE)
    def Release(self):
        print("[!] Advertisement released", flush=True)


class PairingAgent(dbus.service.Object):
    AGENT_PATH = "/org/bluez/piagent"

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.AGENT_PATH)

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        pass

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        pass

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        return "000000"

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        return dbus.UInt32(123456)

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("[Agent] PIN: " + str(pincode), flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print("[Agent] Passkey: %06d (%d typed)" % (passkey, entered), flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("[Agent] Auto-confirm passkey %06d" % passkey, flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print("[Agent] Auto-authorize", flush=True)

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, service_uuid):
        print("[Agent] Authorized " + str(service_uuid), flush=True)


def type_text(text):
    global _report_char
    if not _report_char:
        print("[!] No client subscribed", flush=True)
        return
    for ch in text:
        mod = 0x00
        code = None
        if ch in KEYMAP:
            code = KEYMAP[ch]
        elif ch in SHIFT_KEYMAP:
            code = SHIFT_KEYMAP[ch]
            mod = 0x02
        if code is not None:
            _report_char.send_key(code, mod)


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    agent = PairingAgent(bus)
    agent_mgr = dbus.Interface(bus.get_object(BLUEZ, "/org/bluez"), AGENT_MGR_IFACE)
    agent_mgr.RegisterAgent(PairingAgent.AGENT_PATH, "KeyboardDisplay",
        reply_handler=lambda: print("[+] Agent registered", flush=True),
        error_handler=lambda e: print("[!] Agent error: " + str(e), flush=True))
    agent_mgr.RequestDefaultAgent(PairingAgent.AGENT_PATH,
        reply_handler=lambda: print("[+] Default agent", flush=True),
        error_handler=lambda e: print("[!] Default agent error: " + str(e), flush=True))

    app = Application(bus)
    app.add_service(HIDService(bus, 0))

    gatt_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), GATT_MANAGER_IFACE)

    def gatt_ok():
        print("[+] GATT application registered", flush=True)
        # Verify our objects are accessible
        try:
            om = dbus.Interface(bus.get_object(BLUEZ, "/"), DBUS_OM_IFACE)
            objects = om.GetManagedObjects()
            count = sum(1 for _, i in objects.items() if GATT_SERVICE_IFACE in i)
            print("[+] BlueZ ObjectManager sees " + str(count) + " GATT services (from org.bluez)", flush=True)
        except Exception as ex:
            print("[!] Verify error: " + str(ex), flush=True)

    def gatt_err(e):
        print("[!] GATT registration FAILED: " + str(e), flush=True)

    gatt_mgr.RegisterApplication(app.get_path(), {},
        reply_handler=gatt_ok,
        error_handler=gatt_err)

    ad = Advertisement(bus)
    ad_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), "org.bluez.LEAdvertisingManager1")
    ad_mgr.RegisterAdvertisement(ad.get_path(), {},
        reply_handler=lambda: print("[+] Advertisement registered", flush=True),
        error_handler=lambda e: print("[!] Ad error: " + str(e), flush=True))

    props = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), DBUS_PROP_IFACE)
    props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
    props.Set("org.bluez.Adapter1", "Alias", "Pi Keyboard")
    props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
    props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))

    if os.path.exists(CMD_SOCKET):
        os.remove(CMD_SOCKET)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(CMD_SOCKET)
    srv.listen(1)
    os.chmod(CMD_SOCKET, 0o666)

    def handle_commands():
        while True:
            try:
                conn, _ = srv.accept()
                data = conn.recv(4096)
                if data:
                    text = data.decode("utf-8", errors="replace").strip()
                    print("[>] Type: " + repr(text), flush=True)
                    type_text(text)
                    conn.send(b"OK\n")
                conn.close()
            except Exception as e:
                print("[!] Socket: " + str(e), flush=True)

    threading.Thread(target=handle_commands, daemon=True).start()

    print("[*] BLE HID Keyboard running", flush=True)
    print("[*] Pair as 'Pi Keyboard'", flush=True)
    print("[*] Type: echo hello | socat - UNIX-CONNECT:" + CMD_SOCKET, flush=True)

    loop = GLib.MainLoop()
    loop.run()


if __name__ == "__main__":
    main()
