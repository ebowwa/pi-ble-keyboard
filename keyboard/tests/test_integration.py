"""Tests for the command socket and integration paths.

These tests run on any platform — they mock D-Bus where needed.
"""

import os
import socket
import tempfile
import pytest
from btkeyboard.command_socket import CommandSocket, SOCKET_PATH


class TestCommandSocket:
    def test_command_socket_receives_text(self):
        """Connect, send text, verify callback fires."""
        received = []

        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = os.path.join(tmpdir, "test.sock")
            cmd = CommandSocket(
                on_text_callback=lambda text: received.append(text),
                socket_path=sock_path,
            )
            cmd.start()

            # Give the thread a moment to bind
            import time
            time.sleep(0.1)

            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(sock_path)
            client.send(b"hello world")
            resp = client.recv(1024)
            client.close()

            time.sleep(0.1)

            assert resp == b"OK\n"
            assert received == ["hello world"]

    def test_command_socket_strips_whitespace(self):
        received = []

        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = os.path.join(tmpdir, "test.sock")
            cmd = CommandSocket(
                on_text_callback=lambda text: received.append(text),
                socket_path=sock_path,
            )
            cmd.start()

            import time
            time.sleep(0.1)

            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(sock_path)
            client.send(b"  trimmed  \n")
            resp = client.recv(1024)
            client.close()

            time.sleep(0.1)

            assert received == ["trimmed"]

    def test_socket_cleanup_on_start(self):
        """If a stale socket file exists, it should be removed and re-bound."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sock_path = os.path.join(tmpdir, "test.sock")
            # Create stale file
            with open(sock_path, "w") as f:
                f.write("stale")

            cmd = CommandSocket(
                on_text_callback=lambda _: None,
                socket_path=sock_path,
            )
            cmd.start()

            import time
            time.sleep(0.1)

            # Should be able to connect (stale file was replaced)
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(sock_path)
            client.send(b"test")
            client.recv(1024)
            client.close()


class TestPackageMetadata:
    def test_version_string(self):
        import btkeyboard
        assert btkeyboard.__version__ == "2.0.0"

    def test_all_exports(self):
        import btkeyboard
        for name in btkeyboard.__all__:
            assert hasattr(btkeyboard, name), f"Missing export: {name}"


class TestEndToEndTyping:
    """Integration test: text → reports → mock BLE send."""

    def test_full_pipeline_text_to_ble(self):
        """Simulate the full typing pipeline without BLE hardware."""
        from btkeyboard.typing import type_text_sync

        sent_reports: list[list[int]] = []
        count = type_text_sync("Hello World 123!", send_fn=sent_reports.append)

        assert count == 16  # 16 mappable chars (space included)
        assert len(sent_reports) == 32  # 16 × 2

        # Verify first char 'H' → Shift + h (code 11)
        assert sent_reports[0] == [0x02, 0x00, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00]

        # Verify space at position 10 (char index 5, report 10)
        assert sent_reports[10] == [0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00, 0x00]

        # Verify '!' at end → Shift + 1 (code 30)
        assert sent_reports[30] == [0x02, 0x00, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00]
