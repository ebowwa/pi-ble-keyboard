"""
btkeyboard — BLE HID Keyboard for Raspberry Pi.

Turns a Pi into a Bluetooth Low Energy keyboard that types on iOS devices.
Uses BlueZ's GATT API with pure Boot Protocol (8-byte reports, no Report ID).
"""

from __future__ import annotations
from .keymap import KEYMAP, SHIFT_KEYMAP, char_to_hid
from .hid_descriptor import HID_REPORT_MAP, HID_INFORMATION, PROTOCOL_MODE_REPORT
from .report import BootProtocolReport, MOD_LSHIFT, MOD_LCTRL, MOD_LALT, MOD_LGUI

__version__ = "2.0.0"

__all__ = [
    "KEYMAP",
    "SHIFT_KEYMAP",
    "char_to_hid",
    "HID_REPORT_MAP",
    "HID_INFORMATION",
    "PROTOCOL_MODE_REPORT",
    "BootProtocolReport",
    "MOD_LSHIFT",
    "MOD_LCTRL",
    "MOD_LALT",
    "MOD_LGUI",
    "__version__",
]
