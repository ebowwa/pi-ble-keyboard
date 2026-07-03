"""
Unix socket command server for mouse input.

Accepts JSON commands on /tmp/bt_mouse.sock:

    {"cmd": "move", "dx": 10, "dy": -5}
    {"cmd": "scroll", "amount": 5}
    {"cmd": "click", "button": "left"}
    {"cmd": "click", "button": "right"}
    {"cmd": "down", "button": "left"}
    {"cmd": "up"}
    {"cmd": "drag", "dx": 50, "dy": 30}

Usage:
    echo '{"cmd":"move","dx":10,"dy":0}' | socat - UNIX-CONNECT:/tmp/bt_mouse.sock
    echo '{"cmd":"click","button":"left"}' | socat - UNIX-CONNECT:/tmp/bt_mouse.sock
"""

from __future__ import annotations
import socket
import os
import json
import threading

SOCKET_PATH = "/tmp/bt_mouse.sock"

BUTTON_MAP = {
    "left": 0x01,
    "right": 0x02,
    "middle": 0x04,
}


class MouseCommandSocket:
    """Threaded Unix socket server that processes mouse commands."""

    def __init__(self, on_command_callback, socket_path=SOCKET_PATH):
        self.on_command_callback = on_command_callback
        self.socket_path = socket_path
        self._srv = None
        self._thread = None

    def start(self):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        self._srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv.bind(self.socket_path)
        self._srv.listen(1)
        os.chmod(self.socket_path, 0o666)

        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[*] Mouse socket listening on {self.socket_path}", flush=True)

    def _listen_loop(self):
        while True:
            try:
                conn, _ = self._srv.accept()
                data = conn.recv(4096)
                if data:
                    raw = data.decode("utf-8", errors="replace").strip()
                    print(f"[>] Command: {raw}", flush=True)
                    reports = parse_command(raw)
                    if reports:
                        self.on_command_callback(reports)
                        conn.send(b"OK\n")
                    else:
                        conn.send(b"ERR: bad command\n")
                conn.close()
            except Exception as e:
                print(f"[!] Socket error: {e}", flush=True)


def parse_command(raw: str) -> list[dict] | None:
    """Parse a JSON command string into a list of report dicts.

    Returns None if the command is invalid.
    """
    try:
        cmd = json.loads(raw)
    except json.JSONDecodeError:
        return None

    action = cmd.get("cmd", "").lower()
    reports = []

    if action == "move":
        dx = int(cmd.get("dx", 0))
        dy = int(cmd.get("dy", 0))
        reports.append({"buttons": 0, "x": dx, "y": dy, "wheel": 0})

    elif action == "scroll":
        amount = int(cmd.get("amount", 0))
        reports.append({"buttons": 0, "x": 0, "y": 0, "wheel": amount})

    elif action == "click":
        btn_name = cmd.get("button", "left")
        btn = BUTTON_MAP.get(btn_name, 0x01)
        reports.append({"buttons": btn, "x": 0, "y": 0, "wheel": 0})
        reports.append({"buttons": 0, "x": 0, "y": 0, "wheel": 0})

    elif action == "double":
        btn_name = cmd.get("button", "left")
        btn = BUTTON_MAP.get(btn_name, 0x01)
        for _ in range(2):
            reports.append({"buttons": btn, "x": 0, "y": 0, "wheel": 0})
            reports.append({"buttons": 0, "x": 0, "y": 0, "wheel": 0})

    elif action == "down":
        btn_name = cmd.get("button", "left")
        btn = BUTTON_MAP.get(btn_name, 0x01)
        reports.append({"buttons": btn, "x": 0, "y": 0, "wheel": 0})

    elif action == "up":
        reports.append({"buttons": 0, "x": 0, "y": 0, "wheel": 0})

    elif action == "drag":
        dx = int(cmd.get("dx", 0))
        dy = int(cmd.get("dy", 0))
        btn = BUTTON_MAP.get(cmd.get("button", "left"), 0x01)
        reports.append({"buttons": btn, "x": 0, "y": 0, "wheel": 0})  # down
        # Move in small steps
        steps = max(1, max(abs(dx), abs(dy)) // 10)
        for i in range(1, steps + 1):
            sx = dx * i // steps - dx * (i - 1) // steps
            sy = dy * i // steps - dy * (i - 1) // steps
            reports.append({"buttons": btn, "x": sx, "y": sy, "wheel": 0})
        reports.append({"buttons": 0, "x": 0, "y": 0, "wheel": 0})  # up

    else:
        return None

    return reports
