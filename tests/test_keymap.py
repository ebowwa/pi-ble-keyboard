"""Exhaustive tests for the HID keymap (char → usage code + modifier)."""

import pytest
from btkeyboard.keymap import (
    KEYMAP,
    SHIFT_KEYMAP,
    char_to_hid,
    MOD_LSHIFT,
    MOD_LCTRL,
    MOD_LALT,
    MOD_LGUI,
    MOD_RCTRL,
    MOD_RSHIFT,
    MOD_RALT,
    MOD_RGUI,
    MOD_LCTRL,
)


class TestKeymapCompleteness:
    """Every printable ASCII char (32–126) must be mappable."""

    def test_all_lowercase_letters(self):
        for ch in "abcdefghijklmnopqrstuvwxyz":
            assert ch in KEYMAP, f"Missing lowercase: {ch!r}"

    def test_all_uppercase_letters(self):
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert ch in SHIFT_KEYMAP, f"Missing uppercase: {ch!r}"

    def test_all_digits(self):
        for ch in "0123456789":
            assert ch in KEYMAP, f"Missing digit: {ch!r}"

    def test_all_punctuation_unshifted(self):
        for ch in " -=[]\\;'`,./\n\t":
            assert ch in KEYMAP, f"Missing unshifted punctuation: {ch!r}"

    def test_all_punctuation_shifted(self):
        for ch in "?!@#$%^&*()_+{}|:\"~<>":
            assert ch in SHIFT_KEYMAP, f"Missing shifted punctuation: {ch!r}"

    def test_all_printable_ascii_mappable(self):
        """Every printable ASCII char (32–126) should be in at least one keymap."""
        unmapped = []
        for code in range(32, 127):
            ch = chr(code)
            if ch not in KEYMAP and ch not in SHIFT_KEYMAP:
                unmapped.append(ch)
        assert not unmapped, f"Unmapped printable ASCII chars: {unmapped}"


class TestKeymapCorrectness:
    """Verify specific HID usage codes match the USB HID spec."""

    @pytest.mark.parametrize("char,expected_code", [
        ("a", 4), ("b", 5), ("c", 6), ("z", 29),
        ("1", 30), ("2", 31), ("9", 38), ("0", 39),
        (" ", 44), ("\n", 40), ("\t", 43),
        ("-", 45), ("=", 46), ("[", 47), ("]", 48),
        ("\\", 49), (";", 51), ("'", 52), ("`", 50),
        (",", 53), (".", 54), ("/", 55),
    ])
    def test_keymap_codes(self, char, expected_code):
        assert KEYMAP[char] == expected_code

    @pytest.mark.parametrize("char,expected_code", [
        ("A", 4), ("Z", 29),
        ("!", 30), ("@", 31), ("#", 32),
        ("(", 38), (")", 39),
        ("_", 45), ("+", 46), ("{", 47), ("}", 48),
        ("|", 49), (":", 51), ('"', 52), ("~", 50),
        ("<", 53), (">", 54), ("?", 55),
    ])
    def test_shift_keymap_codes(self, char, expected_code):
        assert SHIFT_KEYMAP[char] == expected_code

    def test_uppercase_and_lowercase_share_usage_code(self):
        """A and a should map to the same HID usage code (4), differing only in modifier."""
        assert KEYMAP["a"] == SHIFT_KEYMAP["A"] == 4
        assert KEYMAP["z"] == SHIFT_KEYMAP["Z"] == 29

    def test_shifted_digit_pairs(self):
        """Each digit and its shifted counterpart should share a usage code."""
        pairs = [("1", "!"), ("2", "@"), ("3", "#"), ("4", "$"), ("5", "%"),
                 ("6", "^"), ("7", "&"), ("8", "*"), ("9", "("), ("0", ")")]
        for unshifted, shifted in pairs:
            assert KEYMAP[unshifted] == SHIFT_KEYMAP[shifted], \
                f"{unshifted!r} and {shifted!r} should share usage code"


class TestCharToHid:
    """Test the char_to_hid() conversion function."""

    def test_lowercase_returns_no_modifier(self):
        mod, code = char_to_hid("a")
        assert mod == 0x00
        assert code == 4

    def test_uppercase_returns_shift_modifier(self):
        mod, code = char_to_hid("A")
        assert mod == MOD_LSHIFT  # 0x02
        assert code == 4

    def test_space(self):
        mod, code = char_to_hid(" ")
        assert mod == 0x00
        assert code == 44

    def test_newline(self):
        mod, code = char_to_hid("\n")
        assert mod == 0x00
        assert code == 40

    def test_tab(self):
        mod, code = char_to_hid("\t")
        assert mod == 0x00
        assert code == 43

    def test_unmapped_char_returns_none(self):
        assert char_to_hid("\x01") is None  # control char
        assert char_to_hid("é") is None     # non-ASCII
        assert char_to_hid("🎉") is None    # emoji

    @pytest.mark.parametrize("char", list("abcdefghijklmnopqrstuvwxyz"))
    def test_all_lowercase_no_modifier(self, char):
        mod, _ = char_to_hid(char)
        assert mod == 0x00

    @pytest.mark.parametrize("char", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    def test_all_uppercase_shift_modifier(self, char):
        mod, _ = char_to_hid(char)
        assert mod == MOD_LSHIFT


class TestModifierMasks:
    """Verify modifier bitmask values match the USB HID spec."""

    def test_modifier_values(self):
        assert MOD_LCTRL == 0x01
        assert MOD_LSHIFT == 0x02
        assert MOD_LALT == 0x04
        assert MOD_LGUI == 0x08
        assert MOD_RCTRL == 0x10
        assert MOD_RSHIFT == 0x20
        assert MOD_RALT == 0x40
        assert MOD_RGUI == 0x80

    def test_all_modifiers_sum_to_0xFF(self):
        """All 8 modifier bits set should equal 0xFF."""
        all_mods = MOD_LCTRL | MOD_LSHIFT | MOD_LALT | MOD_LGUI | \
                   MOD_RCTRL | MOD_RSHIFT | MOD_RALT | MOD_RGUI
        assert all_mods == 0xFF

    def test_modifiers_are_single_bits(self):
        """Each modifier should be exactly one bit."""
        for mod in [MOD_LCTRL, MOD_LSHIFT, MOD_LALT, MOD_LGUI,
                    MOD_RCTRL, MOD_RSHIFT, MOD_RALT, MOD_RGUI]:
            assert mod != 0 and (mod & (mod - 1)) == 0, \
                f"{mod:#x} is not a single bit"
