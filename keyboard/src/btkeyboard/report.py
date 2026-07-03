"""
HID Boot Protocol Report encoder.

Builds the 8-byte report that goes over BLE LE notifications to iOS.
Format (no Report ID prefix):

    Byte 0: Modifier flags (Ctrl/Shift/Alt/GUI × L/R)
    Byte 1: Reserved (always 0x00)
    Byte 2-7: Up to 6 simultaneous keycodes (first unused = 0x00)

A key press is: [mod, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00]
A key release is: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from .keymap import MOD_LSHIFT, MOD_LCTRL, MOD_LALT, MOD_LGUI


REPORT_SIZE = 8  # Boot Protocol: always 8 bytes


@dataclass
class BootProtocolReport:
    """A single 8-byte HID Boot Protocol keyboard report."""

    modifier: int = 0x00
    reserved: int = 0x00  # always 0x00 per spec
    keycodes: list[int] = field(default_factory=lambda: [0x00] * 6)

    def __post_init__(self):
        self.validate()

    def validate(self):
        """Raise ValueError if the report doesn't conform to Boot Protocol."""
        if not (0x00 <= self.modifier <= 0xFF):
            raise ValueError(f"Modifier byte out of range: {self.modifier:#x}")
        if self.reserved != 0x00:
            raise ValueError(f"Reserved byte must be 0x00, got {self.reserved:#x}")
        if len(self.keycodes) != 6:
            raise ValueError(f"Expected 6 keycode slots, got {len(self.keycodes)}")
        for kc in self.keycodes:
            if not (0x00 <= kc <= 0xFF):
                raise ValueError(f"Keycode out of range: {kc:#x}")

    def to_bytes(self) -> list[int]:
        """Return the 8-byte report as a list of ints (for BlueZ dbus.Array)."""
        return [self.modifier, self.reserved] + self.keycodes

    @classmethod
    def key_press(cls, keycode: int, modifier: int = 0x00) -> "BootProtocolReport":
        """Create a key-press report: single key held down."""
        return cls(modifier=modifier, keycodes=[keycode, 0, 0, 0, 0, 0])

    @classmethod
    def key_release(cls) -> "BootProtocolReport":
        """Create a key-release report: all keys released."""
        return cls()

    @classmethod
    def from_char(cls, char: str) -> tuple["BootProtocolReport", "BootProtocolReport"] | None:
        """Create a press+release pair for a single character.

        Returns None if the character is not mappable.
        """
        from .keymap import char_to_hid
        result = char_to_hid(char)
        if result is None:
            return None
        modifier, keycode = result
        return (
            cls.key_press(keycode, modifier),
            cls.key_release(),
        )

    def __eq__(self, other):
        if isinstance(other, list):
            return self.to_bytes() == other
        if isinstance(other, BootProtocolReport):
            return self.to_bytes() == other.to_bytes()
        return NotImplemented

    def __repr__(self):
        return f"BootProtocolReport({self.to_bytes()})"
