"""
USB HID Report Descriptor for a standard mouse (Boot Protocol).

4-byte mouse reports, no Report ID prefix:
    Byte 0: Button states (bit 0=left, 1=right, 2=middle, 3-7=padding)
    Byte 1: X movement (-127 to +127)
    Byte 2: Y movement (-127 to +127)
    Byte 3: Wheel (-127 to +127)

References:
  - USB HID Specification, Appendix B.2 (Boot Protocol Mouse)
  - Bluetooth HID Service Specification (HOGP)
"""

# HID Service UUID
HID_SVC = "00001812-0000-1000-8000-00805f9b34fb"

# Characteristic UUIDs
HID_INFO_UUID = "00002A4A-0000-1000-8000-00805f9b34fb"
HID_REPORT_MAP_UUID = "00002A4B-0000-1000-8000-00805f9b34fb"
HID_CTRL_UUID = "00002A4C-0000-1000-8000-00805f9b34fb"
HID_REPORT_UUID = "00002A4D-0000-1000-8000-00805f9b34fb"
HID_PROTO_UUID = "00002A4E-0000-1000-8000-00805f9b34fb"
REPORT_REF_UUID = "00002908-0000-1000-8000-00805f9b34fb"

# HID Information: version=1.1, country=0, flags=0
HID_INFORMATION = [0x01, 0x01, 0x00, 0x02]

# Report Reference for Boot Mouse: Report ID=0, Report Type=Input
REPORT_REF_BOOT_MOUSE = [0x00, 0x01]

# Standard HID Mouse Report Map (no Report ID — Boot Protocol)
MOUSE_REPORT_MAP = [
    0x05, 0x01,        # Usage Page (Generic Desktop Ctrls)
    0x09, 0x02,        # Usage (Mouse)
    0xA1, 0x01,        # Collection (Application)
    # ── Pointer physical collection ──
    0x09, 0x01,        #   Usage (Pointer)
    0xA1, 0x00,        #   Collection (Physical)
    # ── Buttons (3 buttons, 5 padding bits) ──
    0x05, 0x09,        #   Usage Page (Button)
    0x19, 0x01,        #   Usage Minimum (0x01)
    0x29, 0x03,        #   Usage Maximum (0x03)
    0x15, 0x00,        #   Logical Minimum (0)
    0x25, 0x01,        #   Logical Maximum (1)
    0x95, 0x03,        #   Report Count (3)
    0x75, 0x01,        #   Report Size (1)
    0x81, 0x02,        #   Input (Data,Var,Abs)
    # ── Button padding (5 bits) ──
    0x95, 0x01,        #   Report Count (1)
    0x75, 0x05,        #   Report Size (5)
    0x81, 0x01,        #   Input (Const,Array,Abs)
    # ── X, Y, Wheel ──
    0x05, 0x01,        #   Usage Page (Generic Desktop Ctrls)
    0x09, 0x30,        #   Usage (X)
    0x09, 0x31,        #   Usage (Y)
    0x09, 0x38,        #   Usage (Wheel)
    0x15, 0x81,        #   Logical Minimum (-127)
    0x25, 0x7F,        #   Logical Maximum (127)
    0x75, 0x08,        #   Report Size (8)
    0x95, 0x03,        #   Report Count (3)
    0x81, 0x06,        #   Input (Data,Var,Rel)
    0xC0,              #   End Collection (Physical)
    0xC0,              # End Collection (Application)
]
