"""Exhaustive tests for the Boot Protocol report encoder."""

import pytest
from btkeyboard.report import BootProtocolReport, REPORT_SIZE


class TestReportSize:
    def test_report_size_is_8(self):
        assert REPORT_SIZE == 8

    def test_key_press_report_is_8_bytes(self):
        report = BootProtocolReport.key_press(4)
        assert len(report.to_bytes()) == 8

    def test_key_release_report_is_8_bytes(self):
        report = BootProtocolReport.key_release()
        assert len(report.to_bytes()) == 8


class TestKeyPressReport:
    def test_basic_key_press(self):
        report = BootProtocolReport.key_press(4)  # 'a'
        assert report.to_bytes() == [0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_shifted_key_press(self):
        report = BootProtocolReport.key_press(4, modifier=0x02)  # 'A'
        assert report.to_bytes() == [0x02, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_modifier_only_press(self):
        """Just Shift down, no keycode — like a bare modifier key."""
        report = BootProtocolReport.key_press(0, modifier=0x02)
        assert report.to_bytes() == [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_keycode_in_correct_position(self):
        """The keycode must always be at byte index 2 (third byte)."""
        for code in [4, 10, 20, 30, 44, 55]:
            report = BootProtocolReport.key_press(code)
            assert report.to_bytes()[2] == code

    def test_modifier_in_byte_zero(self):
        """The modifier must always be at byte index 0."""
        for mod in [0x00, 0x01, 0x02, 0x04, 0x08, 0xFF]:
            report = BootProtocolReport.key_press(4, modifier=mod)
            assert report.to_bytes()[0] == mod


class TestKeyReleaseReport:
    def test_release_is_all_zeros(self):
        report = BootProtocolReport.key_release()
        assert report.to_bytes() == [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_release_default_constructor(self):
        report = BootProtocolReport()
        assert report.to_bytes() == [0] * 8

    def test_release_modifier_is_zero(self):
        report = BootProtocolReport.key_release()
        assert report.to_bytes()[0] == 0x00


class TestReportFromChar:
    @pytest.mark.parametrize("char,modifier,keycode", [
        ("a", 0x00, 4), ("z", 0x00, 29),
        ("A", 0x02, 4), ("Z", 0x02, 29),
        ("1", 0x00, 30), ("!", 0x02, 30),
        (" ", 0x00, 44), ("\n", 0x00, 40),
    ])
    def test_from_char_produces_correct_press(self, char, modifier, keycode):
        pair = BootProtocolReport.from_char(char)
        assert pair is not None
        press, release = pair
        assert press.to_bytes() == [modifier, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00]
        assert release.to_bytes() == [0x00] * 8

    def test_from_char_unmapped_returns_none(self):
        assert BootProtocolReport.from_char("é") is None
        assert BootProtocolReport.from_char("\x00") is None


class TestReportValidation:
    def test_reserved_byte_must_be_zero(self):
        with pytest.raises(ValueError, match="Reserved"):
            BootProtocolReport(reserved=0x01)

    def test_modifier_range(self):
        with pytest.raises(ValueError, match="Modifier"):
            BootProtocolReport(modifier=0x100)

    def test_wrong_keycode_count(self):
        with pytest.raises(ValueError, match="6 keycode"):
            BootProtocolReport(keycodes=[0, 0, 0])

    def test_keycode_range(self):
        with pytest.raises(ValueError, match="Keycode"):
            BootProtocolReport(keycodes=[0x100, 0, 0, 0, 0, 0])

    def test_valid_report_no_error(self):
        """A well-formed report should not raise."""
        BootProtocolReport(modifier=0x02, keycodes=[4, 0, 0, 0, 0, 0])

    def test_negative_modifier_raises(self):
        with pytest.raises(ValueError):
            BootProtocolReport(modifier=-1)


class TestReportEq:
    def test_eq_with_list(self):
        report = BootProtocolReport.key_press(4)
        assert report == [0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_eq_with_other_report(self):
        r1 = BootProtocolReport.key_press(4)
        r2 = BootProtocolReport.key_press(4)
        assert r1 == r2

    def test_neq_different_keycode(self):
        r1 = BootProtocolReport.key_press(4)
        r2 = BootProtocolReport.key_press(5)
        assert r1 != r2

    def test_neq_different_modifier(self):
        r1 = BootProtocolReport.key_press(4, 0x00)
        r2 = BootProtocolReport.key_press(4, 0x02)
        assert r1 != r2

    def test_release_eq_all_zeros(self):
        assert BootProtocolReport.key_release() == [0] * 8


class TestBootProtocolNoReportId:
    """Critical: Boot Protocol reports must NOT have a Report ID prefix."""

    def test_press_report_starts_with_modifier_not_report_id(self):
        """The first byte is the modifier, not a Report ID.
        If Report ID were present, byte 0 would be the ID (e.g., 1) and
        the actual report would start at byte 1 (total 9 bytes)."""
        report = BootProtocolReport.key_press(4, modifier=0x02)
        bytes_out = report.to_bytes()
        assert len(bytes_out) == 8  # Not 9 (which would indicate a Report ID)
        assert bytes_out[0] == 0x02  # Modifier, not Report ID
        assert bytes_out[1] == 0x00  # Reserved
        assert bytes_out[2] == 0x04  # Keycode

    def test_no_report_id_byte_anywhere(self):
        """In Boot Protocol, there is no Report ID tag. Verify the structure."""
        report = BootProtocolReport.key_press(29, modifier=0x02)
        b = report.to_bytes()
        # Structure: [modifier, reserved, kc1, kc2, kc3, kc4, kc5, kc6]
        assert b[0] == 0x02  # modifier
        assert b[1] == 0x00  # reserved
        assert b[2] == 29    # first keycode
        assert b[3:8] == [0, 0, 0, 0, 0]  # remaining keycodes empty
