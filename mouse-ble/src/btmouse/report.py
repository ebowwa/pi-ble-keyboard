"""
HID Boot Protocol Mouse report encoder.

Builds 4-byte reports for BLE LE notifications:
    [buttons, X, Y, wheel]

Button bits: 0=left, 1=right, 2=middle
X/Y/Wheel: signed relative movement (-127 to +127)
"""

from __future__ import annotations
from dataclasses import dataclass

REPORT_SIZE = 4  # Boot Protocol mouse: always 4 bytes

# Button masks
BUTTON_LEFT = 0x01
BUTTON_RIGHT = 0x02
BUTTON_MIDDLE = 0x04


def _clamp(val: int) -> int:
    """Clamp to signed byte range [-127, 127]."""
    return max(-127, min(127, val))


def _to_unsigned(val: int) -> int:
    """Convert signed to unsigned byte."""
    return val & 0xFF


@dataclass
class MouseReport:
    """A single 4-byte HID Boot Protocol mouse report."""

    buttons: int = 0x00
    x: int = 0
    y: int = 0
    wheel: int = 0

    def to_bytes(self) -> list[int]:
        """Return the 4-byte report as a list of ints."""
        return [
            self.buttons & 0x07,       # 3 button bits + padding
            _to_unsigned(_clamp(self.x)),
            _to_unsigned(_clamp(self.y)),
            _to_unsigned(_clamp(self.wheel)),
        ]

    # ── Factory methods ──

    @classmethod
    def move(cls, dx: int = 0, dy: int = 0, wheel: int = 0) -> "MouseReport":
        """Move cursor by relative dx/dy, scroll by wheel."""
        return cls(x=dx, y=dy, wheel=wheel)

    @classmethod
    def click(cls, button: int = BUTTON_LEFT) -> "MouseReport":
        """Press a button (no movement)."""
        return cls(buttons=button)

    @classmethod
    def release(cls) -> "MouseReport":
        """Release all buttons."""
        return cls()

    @classmethod
    def left_click(cls) -> "MouseReport":
        """Left button down."""
        return cls(buttons=BUTTON_LEFT)

    @classmethod
    def right_click(cls) -> "MouseReport":
        """Right button down."""
        return cls(buttons=BUTTON_RIGHT)

    @classmethod
    def middle_click(cls) -> "MouseReport":
        """Middle button down."""
        return cls(buttons=BUTTON_MIDDLE)

    def __eq__(self, other):
        if isinstance(other, list):
            return self.to_bytes() == other
        if isinstance(other, MouseReport):
            return self.to_bytes() == other.to_bytes()
        return NotImplemented

    def __repr__(self):
        return f"MouseReport(buttons={self.buttons:#04x}, x={self.x}, y={self.y}, wheel={self.wheel})"
