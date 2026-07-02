"""
Unix socket command server — receives text to type.

Listens on /tmp/bt_keyboard.sock for connections. Each connection sends
UTF-8 text, which gets typed on the connected iOS device via BLE HID.

Usage:
    echo "hello" | socat - UNIX-CONNECT:/tmp/bt_keyboard.sock
    echo "hello" | ssh pi@pi-ip 'socat - UNIX-CONNECT:/tmp/bt_keyboard.sock'
"""

from __future__ import annotations
import socket
import os
import threading

SOCKET_PATH = "/tmp/bt_keyboard.sock"


class CommandSocket:
    """Threaded Unix socket server that feeds text to the typing engine."""

    def __init__(self, on_text_callback, socket_path=SOCKET_PATH):
        """
        Args:
            on_text_callback: callable(str) called for each received message.
            socket_path: path for the Unix domain socket.
        """
        self.on_text_callback = on_text_callback
        self.socket_path = socket_path
        self._srv = None
        self._thread = None

    def start(self):
        """Bind the socket and start the listener thread."""
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self._srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv.bind(self.socket_path)
        self._srv.listen(1)
        os.chmod(self.socket_path, 0o666)

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[*] Command socket listening on {self.socket_path}", flush=True)

    def _listen_loop(self):
        while True:
            try:
                conn, _ = self._srv.accept()
                data = conn.recv(4096)
                if data:
                    text = data.decode("utf-8", errors="replace").strip()
                    print("[>] Type: " + repr(text), flush=True)
                    self.on_text_callback(text)
                    conn.send(b"OK\n")
                conn.close()
            except Exception as e:
                print("[!] Socket error: " + str(e), flush=True)
