"""
Typing engine — converts text to HID report sequences.

Abstracts the key press / release timing so the GATT layer just calls
``send_reports(report_list)`` for each character without knowing about
keymaps or modifiers.
"""

from __future__ import annotations
import time
from .report import BootProtocolReport
from .keymap import char_to_hid


# Default inter-key delay (40ms). iOS processes BLE notifications at ~25Hz.
DEFAULT_KEY_DELAY = 0.04


def text_to_reports(text: str, key_delay: float = DEFAULT_KEY_DELAY) -> list[tuple[list[int], float]]:
    """Convert a string into a sequence of (report_bytes, delay_after) tuples.

    Each character generates two reports: press then release.
    Characters not in the keymap are silently skipped.

    Returns a flat list suitable for replay:
        [(press_bytes, delay), (release_bytes, delay), ...]
    """
    reports: list[tuple[list[int], float]] = []
    for char in text:
        mapping = char_to_hid(char)
        if mapping is None:
            continue
        modifier, keycode = mapping
        press = BootProtocolReport.key_press(keycode, modifier)
        release = BootProtocolReport.key_release()
        reports.append((press.to_bytes(), key_delay))
        reports.append((release.to_bytes(), key_delay))
    return reports


def type_text_sync(
    text: str,
    send_fn,
    key_delay: float = DEFAULT_KEY_DELAY,
) -> int:
    """Type text synchronously by calling ``send_fn(report_bytes)`` for each report.

    ``send_fn`` is a callable that accepts a list[int] (the 8-byte report).
    Returns the number of characters successfully typed.
    """
    count = 0
    for char in text:
        mapping = char_to_hid(char)
        if mapping is None:
            continue
        modifier, keycode = mapping
        press = BootProtocolReport.key_press(keycode, modifier)
        release = BootProtocolReport.key_release()

        send_fn(press.to_bytes())
        time.sleep(key_delay)
        send_fn(release.to_bytes())
        time.sleep(key_delay)
        count += 1
    return count
