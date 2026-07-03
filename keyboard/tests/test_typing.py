"""Tests for the typing engine — text → HID report sequence."""

import pytest
from btkeyboard.typing import text_to_reports, type_text_sync, DEFAULT_KEY_DELAY
from btkeyboard.report import BootProtocolReport


class TestTextToReports:
    def test_single_char_produces_two_reports(self):
        """Each char = press + release = 2 reports."""
        reports = text_to_reports("a")
        assert len(reports) == 2

    def test_press_then_release_order(self):
        reports = text_to_reports("a")
        press_bytes, _ = reports[0]
        release_bytes, _ = reports[1]
        # Press: modifier=0, keycode=4
        assert press_bytes == [0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]
        # Release: all zeros
        assert release_bytes == [0x00] * 8

    def test_multi_char_report_count(self):
        reports = text_to_reports("abc")
        assert len(reports) == 6  # 3 chars × 2 reports each

    def test_shifted_chars_have_modifier(self):
        reports = text_to_reports("A")
        press_bytes, _ = reports[0]
        assert press_bytes[0] == 0x02  # Shift modifier

    def test_unmapped_chars_skipped(self):
        reports = text_to_reports("aéb")
        assert len(reports) == 4  # Only 'a' and 'b', 'é' skipped

    def test_empty_string(self):
        assert text_to_reports("") == []

    def test_all_delay_values_present(self):
        reports = text_to_reports("ab")
        for _, delay in reports:
            assert delay == DEFAULT_KEY_DELAY

    def test_alphabet_produces_52_reports(self):
        reports = text_to_reports("abcdefghijklmnopqrstuvwxyz")
        assert len(reports) == 52  # 26 chars × 2

    def test_alphabet_uppercase(self):
        reports = text_to_reports("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        assert len(reports) == 52

    def test_full_printable_ascii(self):
        text = "".join(chr(c) for c in range(32, 127))
        reports = text_to_reports(text)
        # 95 printable chars × 2 = 190 reports
        assert len(reports) == 190

    def test_all_press_reports_have_8_bytes(self):
        reports = text_to_reports("hello world 123")
        for report_bytes, _ in reports:
            assert len(report_bytes) == 8

    def test_all_release_reports_are_zeros(self):
        reports = text_to_reports("test")
        for i in range(1, len(reports), 2):  # odd indices = release
            report_bytes, _ = reports[i]
            assert report_bytes == [0x00] * 8

    def test_space_char(self):
        reports = text_to_reports(" ")
        press_bytes, _ = reports[0]
        assert press_bytes[2] == 44  # space = usage code 44


class TestTypeTextSync:
    def test_types_all_chars(self):
        """type_text_sync should return the count of chars typed."""
        sent: list[list[int]] = []
        count = type_text_sync("hello", send_fn=sent.append)
        assert count == 5
        assert len(sent) == 10  # 5 chars × 2 reports

    def test_skips_unmapped(self):
        count = type_text_sync("aéb", send_fn=lambda _: None)
        assert count == 2

    def test_empty_string(self):
        count = type_text_sync("", send_fn=lambda _: None)
        assert count == 0

    def test_correct_press_release_sequence(self):
        sent: list[list[int]] = []
        type_text_sync("a", send_fn=sent.append)
        assert len(sent) == 2
        assert sent[0] == [0x00, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00]
        assert sent[1] == [0x00] * 8

    def test_shift_modifier_applied(self):
        sent: list[list[int]] = []
        type_text_sync("A", send_fn=sent.append)
        assert sent[0][0] == 0x02  # Shift

    def test_full_typecycle_press_release_pattern(self):
        """For each char: odd-indexed sent[2i] is press, sent[2i+1] is release."""
        sent: list[list[int]] = []
        type_text_sync("abc", send_fn=sent.append)
        for i in range(3):
            press = sent[2 * i]
            release = sent[2 * i + 1]
            assert press != [0] * 8  # press is non-zero (has keycode)
            assert release == [0] * 8  # release is all zeros
