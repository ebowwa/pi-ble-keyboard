#!/usr/bin/env python3
"""
BLE HID Keyboard for Raspberry Pi 4B.
Based on BlueZ example-gatt-server pattern.
Type via: echo "hello" | socat - UNIX-CONNECT:/tmp/bt_keyboard.sock
"""
import dbus
import dbus.exceptions
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

import socket
import os
import threading
import time
import sys

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
LE_ADVERT_IFACE =    'org.bluez.LEAdvertisement1'

ADAPTER_PATH = '/org/bluez/hci0'

HID_SERVICE_UUID =        '00001812-0000-1000-8000-00805f9b34fb'
HID_INFO_UUID =           '00002A4A-0000-1000-8000-00805f9b34fb'
HID_REPORT_MAP_UUID =     '00002A4B-0000-1000-8000-00805f9b34fb'
HID_CTRL_UUID =           '00002A4C-0000-1000-8000-00805f9b34fb'
HID_REPORT_UUID =         '00002A4D-0000-1000-8000-00805f9b34fb'
HID_PROTO_UUID =          '00002A4E-0000-1000-8000-00805f9b34fb'

# Keyboard HID Report Descriptor
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
    'a':4,'b':5,'c':6,'d':7,'e':8,'f':9,'g':10,'h':11,'i':12,'j':13,
    'k':14,'l':15,'m':16,'n':17,'o':18,'p':19,'q':20,'r':21,'s':22,
    't':23,'u':24,'v':25,'w':26,'x':27,'y':28,'z':29,
    '1':30,'2':31,'3':32,'4':33,'5':34,'6':35,'7':36,'8':37,'9':38,'0':39,
    ' ':44,'\n':40,'\t':43,'-':45,'=':46,'[':47,']':48,'\\':49,
    ';':51,"'":52,'`':50,',':53,'.':54,'/':55,
}
SHIFT_KEYMAP = {
    'A':4,'B':5,'C':6,'D':7,'E':8,'F':9,'G':10,'H':11,'I':12,'J':13,
    'K':14,'L':15,'M':16,'N':17,'O':18,'P':19,'Q':20,'R':21,'S':22,
    'T':23,'U':24,'V':25,'W':26,'X':27,'Y':28,'Z':29,
    '!':30,'@':31,'#':32,'$':33,'%':34,'^':35,'&':36,'*':37,'(':38,')':39,
    '_':45,'+':46,'{':47,'}':48,'|':49,':':51,'"':52,'~':50,'<':53,'>':54,'?':55,
}

CMD_SOCKET = '/tmp/bt_keyboard.sock'

# Global ref to the report characteristic for sending notifications
_report_char = None


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
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
    PATH_BASE = ADAPTER_PATH + '/service'

    def __init__(self, bus, index, uuid, primary=True):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, char):
        self.characteristics.append(char)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
            }
        }

    def get_characteristics(self):
        return self.characteristics


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.service = service
        self.value = [0]
        self.notifying = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    def add_descriptor(self, desc):
        self.descriptors.append(desc)

    def get_descriptors(self):
        return []

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        print(f'ReadValue: {self.uuid}')
        return dbus.Array(self.value, signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        print(f'WriteValue: {self.uuid} = {bytes(value).hex()}')
        self.value = list(value)

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        print(f'StartNotify: {self.uuid}')
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        print(f'StopNotify: {self.uuid}')
        self.notifying = False

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def send_notification(self, value):
        self.value = list(value)
        self.PropertiesChanged(
            GATT_CHRC_IFACE,
            {'Value': dbus.Array(self.value, signature='y')},
            [])


class HIDService(Service):
    def __init__(self, bus, index):
        super().__init__(bus, index, HID_SERVICE_UUID, True)
        self.add_characteristic(HIDReportMapChar(bus, 0, self))
        self.add_characteristic(HIDReportChar(bus, 1, self))
        self.add_characteristic(HIDProtocolModeChar(bus, 2, self))
        self.add_characteristic(HIDInfoChar(bus, 3, self))
        self.add_characteristic(HIDCtrlPointChar(bus, 4, self))


class HIDReportMapChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_REPORT_MAP_UUID, ['read'], service)
        self.value = HID_REPORT_MAP


class HIDReportChar(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, HID_REPORT_UUID,
                                ['read', 'notify'], service)
        self.value = [0] * 8

    def StartNotify(self):
        super().StartNotify()
        global _report_char
        _report_char = self
        print('[+] Report notifications enabled — keyboard ready')

    def send_key(self, hid_code, modifier=0):
        self.send_notification([modifier, 0, hid_code, 0, 0, 0, 0, 0])
        time.sleep(0.04)
        self.send_notification([0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.04)


class HIDProtocolModeChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_PROTO_UUID, ['read'], service)
        self.value = [0x01]  # Report protocol mode


class HIDInfoChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_INFO_UUID, ['read'], service)
        self.value = [0x01, 0x01, 0x00, 0x03]


class HIDCtrlPointChar(Characteristic):
    def __init__(self, bus, index, service):
        super().__init__(bus, index, HID_CTRL_UUID, ['write-without-response'], service)


class Advertisement(dbus.service.Object):
    def __init__(self, bus):
        self.path = ADAPTER_PATH + '/advertisement0'
        self.bus = bus
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface == LE_ADVERT_IFACE:
            return {
                'Type': 'peripheral',
                'ServiceUUIDs': dbus.Array([HID_SERVICE_UUID], signature='s'),
                'LocalName': 'Pi Keyboard',
                'Appearance': dbus.UInt16(961),
                'Discoverable': dbus.Boolean(True),
            }
        return {}

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='ss', out_signature='v')
    def Get(self, interface, prop):
        return self.GetAll(interface).get(prop)

    @dbus.service.method(LE_ADVERT_IFACE)
    def Release(self):
        print('[!] Advertisement released')


def type_text(text):
    global _report_char
    if not _report_char:
        print('[!] No client subscribed yet')
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

    # Build GATT app with HID service
    app = Application(bus)
    app.add_service(HIDService(bus, 0))

    # Register GATT
    gatt_mgr = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, ADAPTER_PATH),
        GATT_MANAGER_IFACE)

    def gatt_ok():
        print('[+] GATT application registered')
    def gatt_err(e):
        print(f'[!] GATT error: {e}')

    gatt_mgr.RegisterApplication(app.get_path(), {},
                                 reply_handler=gatt_ok,
                                 error_handler=gatt_err)

    # Register advertisement
    ad = Advertisement(bus)
    ad_mgr = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, ADAPTER_PATH),
        'org.bluez.LEAdvertisingManager1')

    def ad_ok():
        print('[+] Advertisement registered')
    def ad_err(e):
        print(f'[!] Advertisement error: {e}')

    ad_mgr.RegisterAdvertisement(ad.get_path(), {},
                                 reply_handler=ad_ok,
                                 error_handler=ad_err)

    # Make discoverable + pairable
    props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, ADAPTER_PATH),
        DBUS_PROP_IFACE)
    props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))
    props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(True))
    props.Set('org.bluez.Adapter1', 'Pairable', dbus.Boolean(True))

    # Command socket
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
                    text = data.decode('utf-8', errors='replace').strip()
                    print(f'[>] Type: "{text}"')
                    type_text(text)
                    conn.send(b'OK\n')
                conn.close()
            except Exception as e:
                print(f'[!] Socket: {e}')

    threading.Thread(target=handle_commands, daemon=True).start()

    print('[*] BLE HID Keyboard running')
    print('[*] Pair as "Pi Keyboard" from your device')
    print(f'[*] Type: echo "hello" | socat - UNIX-CONNECT:{CMD_SOCKET}')
    print('[*] Ctrl+C to stop')

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()


if __name__ == '__main__':
    main()
