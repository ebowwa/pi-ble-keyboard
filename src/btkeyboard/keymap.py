"""
USB HID keyboard keymap.

Maps ASCII characters to USB HID Usage codes (www.usb.org/hid).
HID usage codes for keyboard/keypad are in range 0x04–0xE7 (usage page 0x07).

References:
  - USB HID Usage Tables, Section 10 (Keyboard/Keypad Page)
  - HID spec, Appendix B.1 (Boot Protocol)
"""

# Lowercase letters, digits, and common punctuation → HID usage code
KEYMAP = {
    # a-z
    "a": 4, "b": 5, "c": 6, "d": 7, "e": 8, "f": 9, "g": 10,
    "h": 11, "i": 12, "j": 13, "k": 14, "l": 15, "m": 16,
    "n": 17, "o": 18, "p": 19, "q": 20, "r": 21, "s": 22,
    "t": 23, "u": 24, "v": 25, "w": 26, "x": 27, "y": 28, "z": 29,
    # 0-9
    "1": 30, "2": 31, "3": 32, "4": 33, "5": 34,
    "6": 35, "7": 36, "8": 37, "9": 38, "0": 39,
    # whitespace / control
    " ": 44, "\n": 40, "\t": 43,
    # punctuation
    "-": 45, "=": 46, "[": 47, "]": 48, "\\": 49,
    ";": 51, "'": 52, "`": 50,
    ",": 53, ".": 54, "/": 55,
}

# Uppercase / shifted characters → HID usage code (Shift modifier required)
SHIFT_KEYMAP = {
    # A-Z
    "A": 4, "B": 5, "C": 6, "D": 7, "E": 8, "F": 9, "G": 10,
    "H": 11, "I": 12, "J": 13, "K": 14, "L": 15, "M": 16,
    "N": 17, "O": 18, "P": 19, "Q": 20, "R": 21, "S": 22,
    "T": 23, "U": 24, "V": 25, "W": 26, "X": 27, "Y": 28, "Z": 29,
    # Shifted digits: ! @ # $ % ^ & * ( )
    "!": 30, "@": 31, "#": 32, "$": 33, "%": 34,
    "^": 35, "&": 36, "*": 37, "(": 38, ")": 39,
    # Shifted punctuation
    "_": 45, "+": 46, "{": 47, "}": 48, "|": 49,
    ":": 51, '"': 52, "~": 50,
    "<": 53, ">": 54, "?": 55,
}

# Modifier byte bitmask values (bits 0–7 of byte 0 in the Boot report)
MOD_LCTRL  = 0x01
MOD_LSHIFT = 0x02
MOD_LALT   = 0x04
MOD_LGUI   = 0x08
MOD_RCTRL  = 0x10
MOD_RSHIFT = 0x20
MOD_RALT   = 0x40
MOD_RGUI   = 0x80


def char_to_hid(char: str) -> tuple[int, int] | None:
    """Convert a single character to ``(modifier_byte, hid_usage_code)``.

    Returns ``(0x00, code)`` for lowercase / unshifted chars,
    ``(0x02, code)`` for uppercase / shifted chars,
    or ``None`` if the char is not in either keymap.
    """
    if char in KEYMAP:
        return (0x00, KEYMAP[char])
    if char in SHIFT_KEYMAP:
        return (MOD_LSHIFT, SHIFT_KEYMAP[char])
    return None
