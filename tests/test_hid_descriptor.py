"""Tests for the HID report descriptor and GATT characteristic UUIDs."""

import pytest
from btkeyboard.hid_descriptor import (
    HID_REPORT_MAP,
    HID_INFORMATION,
    PROTOCOL_MODE_REPORT,
    PROTOCOL_MODE_BOOT,
    HID_CTRL_SUSPEND,
    HID_CTRL_EXIT_SUSPEND,
    REPORT_REF_BOOT_KEYBOARD,
    HID_SVC,
    HID_INFO_UUID,
    HID_REPORT_MAP_UUID,
    HID_CTRL_UUID,
    HID_REPORT_UUID,
    HID_PROTO_UUID,
    REPORT_REF_UUID,
)


class TestHidReportMap:
    """Verify the HID Report Descriptor structure."""

    def test_starts_with_usage_page_generic_desktop(self):
        assert HID_REPORT_MAP[0:2] == [0x05, 0x01]

    def test_usage_is_keyboard(self):
        assert HID_REPORT_MAP[2:4] == [0x09, 0x06]

    def test_collection_is_application(self):
        assert HID_REPORT_MAP[4:6] == [0xA1, 0x01]

    def test_ends_with_end_collection(self):
        assert HID_REPORT_MAP[-1] == 0xC0

    def test_no_report_id_tag(self):
        """0x85 is Report ID. It must NOT appear in the descriptor for Boot Protocol."""
        assert 0x85 not in HID_REPORT_MAP, \
            "Report ID tag (0x85) found in HID Report Map — breaks Boot Protocol"

    def test_modifier_byte_8_bits(self):
        """Report Size=1, Report Count=8 → 8 modifier bits (1 byte)."""
        # Find the modifier section: Usage Min 0xE0, Usage Max 0xE7
        assert 0xE0 in HID_REPORT_MAP
        assert 0xE7 in HID_REPORT_MAP

    def test_six_keycode_slots(self):
        """Report Count=6 for keycodes."""
        assert 0x95 in HID_REPORT_MAP
        # The second occurrence of 0x95 0x06 is the keycode count
        indices = [i for i, v in enumerate(HID_REPORT_MAP) if v == 0x95]
        has_six = any(HID_REPORT_MAP[i+1] == 0x06 for i in indices)
        assert has_six, "No Report Count of 6 found (keycode slots)"

    def test_led_output_report(self):
        """LED Usage Page (0x08) is present."""
        assert 0x08 in HID_REPORT_MAP

    def test_all_bytes_in_valid_range(self):
        """All descriptor items should be bytes (0–255)."""
        for b in HID_REPORT_MAP:
            assert 0 <= b <= 255


class TestHidInformation:
    def test_hid_info_is_4_bytes(self):
        assert len(HID_INFORMATION) == 4

    def test_hid_info_version(self):
        """bcdHID = 0x0101 (HID spec 1.1) stored little-endian."""
        assert HID_INFORMATION[0] == 0x01
        assert HID_INFORMATION[1] == 0x01

    def test_hid_info_country_code(self):
        """Country code 0 = Not Localized."""
        assert HID_INFORMATION[2] == 0x00

    def test_hid_info_flags(self):
        """Flags: 0x03 = RemoteWake + NormallyConnectable."""
        assert HID_INFORMATION[3] == 0x03


class TestProtocolMode:
    def test_report_protocol_mode_value(self):
        assert PROTOCOL_MODE_REPORT == 0x01

    def test_boot_protocol_mode_value(self):
        assert PROTOCOL_MODE_BOOT == 0x00


class TestControlPoint:
    def test_suspend_value(self):
        assert HID_CTRL_SUSPEND == 0x00

    def test_exit_suspend_value(self):
        assert HID_CTRL_EXIT_SUSPEND == 0x01


class TestReportReference:
    def test_report_ref_is_2_bytes(self):
        assert len(REPORT_REF_BOOT_KEYBOARD) == 2

    def test_report_id_is_zero(self):
        """Report ID=0 means no prefix (Boot Protocol)."""
        assert REPORT_REF_BOOT_KEYBOARD[0] == 0x00

    def test_report_type_is_input(self):
        assert REPORT_REF_BOOT_KEYBOARD[1] == 0x01


class TestUuids:
    """Verify all GATT UUIDs follow the Bluetooth Base UUID format."""

    BASE_UUID_SUFFIX = "-0000-1000-8000-00805f9b34fb"

    @pytest.mark.parametrize("uuid", [
        HID_SVC, HID_INFO_UUID, HID_REPORT_MAP_UUID, HID_CTRL_UUID,
        HID_REPORT_UUID, HID_PROTO_UUID,
    ])
    def test_service_uuid_has_base_suffix(self, uuid):
        assert uuid.endswith(self.BASE_UUID_SUFFIX), f"Bad UUID: {uuid}"

    @pytest.mark.parametrize("uuid", [
        HID_SVC, HID_INFO_UUID, HID_REPORT_MAP_UUID, HID_CTRL_UUID,
        HID_REPORT_UUID, HID_PROTO_UUID,
    ])
    def test_uuid_is_lowercase_or_uppercase_canonical(self, uuid):
        """UUIDs should be 36 chars (8-4-4-4-12)."""
        assert len(uuid) == 36, f"Bad UUID length: {uuid}"

    def test_descriptor_uuid_format(self):
        """Report Reference UUID (0x2908) is a short UUID."""
        assert REPORT_REF_UUID == "00002908-0000-1000-8000-00805f9b34fb"

    def test_hid_service_uuid(self):
        assert HID_SVC == "00001812-0000-1000-8000-00805f9b34fb"

    def test_report_uuid(self):
        assert HID_REPORT_UUID == "00002A4D-0000-1000-8000-00805f9b34fb"
