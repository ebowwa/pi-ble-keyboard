"""
USB HID Report Descriptor for a standard keyboard (Boot Protocol).

This is the byte-level descriptor advertised via the HID Report Map
characteristic (UUID 0x2A4B). It describes a single keyboard collection
with:
  - 1 modifier byte   (8 modifier keys as bits)
  - 1 reserved byte   (always 0)
  - 5 LED output bits + 3 padding bits (1 byte total)
  - 6 keycode bytes   (up to 6 simultaneous keys)

No Report ID tag (0x85) is used — this is critical for iOS Boot Protocol
compatibility. Reports are pure 8-byte arrays with no prefix.

References:
  - USB HID Specification, Appendix B.1 (Boot Protocol Keyboard)
  - Bluetooth HID Service Specification (HOGP), Section 3.3
  - https://docs.silabs.com/bluetooth/4.2/hid-over-gatt
"""

from __future__ import annotations
# Standard HID Keyboard Report Map (no Report ID — Boot Protocol)
HID_REPORT_MAP = [
    0x05, 0x01,        # Usage Page (Generic Desktop Ctrls)
    0x09, 0x06,        # Usage (Keyboard)
    0xA1, 0x01,        # Collection (Application)
    # ── Modifier byte ──
    0x05, 0x07,        #   Usage Page (Kbrd/Keypad)
    0x19, 0xE0,        #   Usage Minimum (0xE0)
    0x29, 0xE7,        #   Usage Maximum (0xE7)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x01,        #   Logical Maximum (1)
    0x75, 0x01,        #   Report Size (1)
    0x95, 0x08,        #   Report Count (8)
    0x81, 0x02,        #   Input (Data,Var,Abs)
    # ── Reserved byte ──
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x08,        #   Report Size (8)
    0x81, 0x01,        #   Input (Const,Array,Abs)
    # ── LED output report ──
    0x95, 0x05,        #   Report Count (5)
    0x75, 0x01,        #   Report Size (1)
    0x05, 0x08,        #   Usage Page (LEDs)
    0x19, 0x01,        #   Usage Minimum (Num Lock)
    0x29, 0x05,        #   Usage Maximum (Kana)
    0x91, 0x02,        #   Output (Data,Var,Abs)
    # ── LED padding ──
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x03,        #   Report Size (3)
    0x91, 0x01,        #   Output (Const,Array,Abs)
    # ── Keycodes ──
    0x95, 0x06,        #   Report Count (6)
    0x75, 0x08,        #   Report Size (8)
     0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x65,        #   Logical Maximum (101)
    0x05, 0x07,        #   Usage Page (Kbrd/Keypad)
    0x19, 0x00,        #   Usage Minimum (0x00)
    0x29, 0x65,        #   Usage Maximum (0x65)
    0x81, 0x00,        #   Input (Data,Array,Abs)
    0xC0,              # End Collection
]

# HID Information characteristic value (UUID 0x2A4A)
# Format: [bcdHID, bCountryCode, Remoter (Flags)]
#   bcdHID = 0x1011 (HID Spec 1.1.1) → stored little-endian as 0x11, 0x01
#   bCountryCode = 0x00 (Not Localized)
#   Flags = 0x03 (RemoteWake + NormallyConnectable)
HID_INFORMATION = [0x01, 0x01, 0x00, 0x03]

# Protocol Mode characteristic value (UUID 0x2A4E)
# 0x00 = Boot Protocol Mode, 0x01 = Report Protocol Mode
# iOS initially connects in Report mode but our descriptor is Boot-compatible
PROTOCOL_MODE_REPORT = 0x01
PROTOCOL_MODE_BOOT   = 0x00

# HID Control Point (UUID 0x2A4C)
# 0 = Suspend, 1 = Exit Suspend
HID_CTRL_SUSPEND      = 0x00
HID_CTRL_EXIT_SUSPEND = 0x01

# Report Reference descriptor value (UUID 0x2908)
# Format: [Report ID, Report Type]
#   Report ID = 0 (Boot keyboard input — no ID prefix)
#   Report Type = 1 (Input Report)
REPORT_REF_BOOT_KEYBOARD = [0x00, 0x01]

# GATT service & characteristic UUIDs
HID_SVC              = "00001812-0000-1000-8000-00805f9b34fb"
HID_INFO_UUID        = "00002A4A-0000-1000-8000-00805f9b34fb"
HID_REPORT_MAP_UUID  = "00002A4B-0000-1000-8000-00805f9b34fb"
HID_CTRL_UUID        = "00002A4C-0000-1000-8000-00805f9b34fb"
HID_REPORT_UUID      = "00002A4D-0000-1000-8000-00805f9b34fb"
HID_PROTO_UUID       = "00002A4E-0000-1000-8000-00805f9b34fb"
REPORT_REF_UUID      = "00002908-0000-1000-8000-00805f9b34fb"
