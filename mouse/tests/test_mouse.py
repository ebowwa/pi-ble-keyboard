"""
Test suite for BLE HID Mouse (Boot Protocol).
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from btmouse.report import (
    MouseReport,
    REPORT_SIZE,
    BUTTON_LEFT,
    BUTTON_RIGHT,
    BUTTON_MIDDLE,
)
from btmouse.command_socket import parse_command


class TestMouseReport:
    """Test the MouseReport encoder."""

    def test_default_report(self):
        r = MouseReport()
        assert r.to_bytes() == [0, 0, 0, 0]

    def test_report_size(self):
        assert REPORT_SIZE == 4

    def test_move_right(self):
        r = MouseReport.move(dx=10)
        assert r.to_bytes() == [0, 10, 0, 0]

    def test_move_left(self):
        r = MouseReport.move(dx=-10)
        assert r.to_bytes() == [0, 0xF6, 0, 0]  # -10 = 0xF6 unsigned

    def test_move_up(self):
        r = MouseReport.move(dy=-5)
        assert r.to_bytes() == [0, 0, 0xFB, 0]  # -5 = 0xFB unsigned

    def test_move_down(self):
        r = MouseReport.move(dy=20)
        assert r.to_bytes() == [0, 0, 20, 0]

    def test_move_both(self):
        r = MouseReport.move(dx=10, dy=-20)
        assert r.to_bytes() == [0, 10, 0xEC, 0]  # -20 = 0xEC

    def test_scroll_up(self):
        r = MouseReport.move(wheel=5)
        assert r.to_bytes() == [0, 0, 0, 5]

    def test_scroll_down(self):
        r = MouseReport.move(wheel=-3)
        assert r.to_bytes() == [0, 0, 0, 0xFD]  # -3 = 0xFD

    def test_left_click(self):
        r = MouseReport.left_click()
        assert r.to_bytes() == [BUTTON_LEFT, 0, 0, 0]

    def test_right_click(self):
        r = MouseReport.right_click()
        assert r.to_bytes() == [BUTTON_RIGHT, 0, 0, 0]

    def test_middle_click(self):
        r = MouseReport.middle_click()
        assert r.to_bytes() == [BUTTON_MIDDLE, 0, 0, 0]

    def test_release(self):
        r = MouseReport.release()
        assert r.to_bytes() == [0, 0, 0, 0]

    def test_clamp_max(self):
        r = MouseReport.move(dx=200)
        assert r.to_bytes()[1] == 127  # clamped to 127

    def test_clamp_min(self):
        r = MouseReport.move(dx=-200)
        assert r.to_bytes()[1] == 129  # -127 = 0x81 = 129 unsigned

    def test_button_mask(self):
        r = MouseReport(buttons=BUTTON_LEFT | BUTTON_RIGHT)
        assert r.to_bytes()[0] == 0x03  # left+right

    def test_button_mask_all(self):
        r = MouseReport(buttons=BUTTON_LEFT | BUTTON_RIGHT | BUTTON_MIDDLE)
        assert r.to_bytes()[0] == 0x07

    def test_button_padding_masked(self):
        """Button byte should only have 3 bits, upper 5 masked off."""
        r = MouseReport(buttons=0xFF)
        assert r.to_bytes()[0] == 0x07  # masked to 3 bits

    def test_repr(self):
        r = MouseReport(buttons=1, x=10, y=-5)
        assert "buttons=0x01" in repr(r)
        assert "x=10" in repr(r)

    def test_eq_list(self):
        r = MouseReport.move(dx=5)
        assert r == [0, 5, 0, 0]


class TestCommandParser:
    """Test the JSON command parser."""

    def test_move_command(self):
        reports = parse_command('{"cmd":"move","dx":10,"dy":5}')
        assert reports == [{"buttons": 0, "x": 10, "y": 5, "wheel": 0}]

    def test_move_negative(self):
        reports = parse_command('{"cmd":"move","dx":-10,"dy":-5}')
        assert reports == [{"buttons": 0, "x": -10, "y": -5, "wheel": 0}]

    def test_move_default_zero(self):
        reports = parse_command('{"cmd":"move"}')
        assert reports == [{"buttons": 0, "x": 0, "y": 0, "wheel": 0}]

    def test_scroll_up(self):
        reports = parse_command('{"cmd":"scroll","amount":5}')
        assert reports == [{"buttons": 0, "x": 0, "y": 0, "wheel": 5}]

    def test_scroll_down(self):
        reports = parse_command('{"cmd":"scroll","amount":-3}')
        assert reports == [{"buttons": 0, "x": 0, "y": 0, "wheel": -3}]

    def test_click_left(self):
        reports = parse_command('{"cmd":"click","button":"left"}')
        assert len(reports) == 2  # press + release
        assert reports[0] == {"buttons": 1, "x": 0, "y": 0, "wheel": 0}
        assert reports[1] == {"buttons": 0, "x": 0, "y": 0, "wheel": 0}

    def test_click_right(self):
        reports = parse_command('{"cmd":"click","button":"right"}')
        assert reports[0]["buttons"] == 2

    def test_click_middle(self):
        reports = parse_command('{"cmd":"click","button":"middle"}')
        assert reports[0]["buttons"] == 4

    def test_click_default_left(self):
        reports = parse_command('{"cmd":"click"}')
        assert reports[0]["buttons"] == 1

    def test_double_click(self):
        reports = parse_command('{"cmd":"double","button":"left"}')
        assert len(reports) == 4  # 2 press+release pairs

    def test_down_command(self):
        reports = parse_command('{"cmd":"down","button":"left"}')
        assert len(reports) == 1
        assert reports[0]["buttons"] == 1

    def test_up_command(self):
        reports = parse_command('{"cmd":"up"}')
        assert len(reports) == 1
        assert reports[0]["buttons"] == 0

    def test_drag_command(self):
        reports = parse_command('{"cmd":"drag","dx":50,"dy":30}')
        assert len(reports) >= 3  # down + moves + up
        assert reports[0]["buttons"] == 1  # button down
        assert reports[-1]["buttons"] == 0  # button up

    def test_drag_total_movement(self):
        reports = parse_command('{"cmd":"drag","dx":50,"dy":30}')
        total_x = sum(r["x"] for r in reports[1:-1])  # exclude down/up
        total_y = sum(r["y"] for r in reports[1:-1])
        assert total_x == 50
        assert total_y == 30

    def test_invalid_json(self):
        assert parse_command("not json") is None

    def test_unknown_command(self):
        assert parse_command('{"cmd":"explode"}') is None

    def test_missing_cmd_key(self):
        assert parse_command('{"dx":10}') is None


class TestHIDDescriptor:
    """Test the HID descriptor constants."""

    def test_report_map_starts_correctly(self):
        from btmouse.hid_descriptor import MOUSE_REPORT_MAP
        # Usage Page (Generic Desktop)
        assert MOUSE_REPORT_MAP[0:2] == [0x05, 0x01]
        # Usage (Mouse)
        assert MOUSE_REPORT_MAP[2:4] == [0x09, 0x02]

    def test_report_map_has_pointer_collection(self):
        from btmouse.hid_descriptor import MOUSE_REPORT_MAP
        # Usage (Pointer) = 0x09, 0x01
        assert 0x09 in MOUSE_REPORT_MAP
        assert 0x01 in MOUSE_REPORT_MAP

    def test_report_map_has_x_y_wheel(self):
        from btmouse.hid_descriptor import MOUSE_REPORT_MAP
        # Usage (X) = 0x09, 0x30
        # Usage (Y) = 0x09, 0x31
        # Usage (Wheel) = 0x09, 0x38
        flat = MOUSE_REPORT_MAP
        assert 0x30 in flat  # X
        assert 0x31 in flat  # Y
        assert 0x38 in flat  # Wheel

    def test_report_map_has_relative_input(self):
        from btmouse.hid_descriptor import MOUSE_REPORT_MAP
        # Input (Data,Var,Rel) = 0x81, 0x06
        assert 0x06 in MOUSE_REPORT_MAP  # Relative flag

    def test_report_map_ends_with_end_collection(self):
        from btmouse.hid_descriptor import MOUSE_REPORT_MAP
        assert MOUSE_REPORT_MAP[-1] == 0xC0  # End Collection
        assert MOUSE_REPORT_MAP[-2] == 0xC0  # End Collection

    def test_report_ref_boot_mouse(self):
        from btmouse.hid_descriptor import REPORT_REF_BOOT_MOUSE
        assert REPORT_REF_BOOT_MOUSE == [0x00, 0x01]  # ID=0, Type=Input

    def test_hid_svc_uuid(self):
        from btmouse.hid_descriptor import HID_SVC
        assert HID_SVC == "00001812-0000-1000-8000-00805f9b34fb"

    def test_hid_info_value(self):
        from btmouse.hid_descriptor import HID_INFORMATION
        assert len(HID_INFORMATION) == 4
