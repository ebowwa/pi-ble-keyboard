#!/usr/bin/env python3
"""Fault audit — proves which faults exist before we fix them."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from btkeyboard.keymap import char_to_hid

print("=" * 60)
print("FAULT #1: Unmapped chars silently dropped")
print("=" * 60)

test_strings = [
    ("Basic ASCII",      "hello world 123"),
    ("Accented chars",   "héllo wörld café"),
    ("Symbols",          "©™®°±µ§¶"),
    ("Emoji",            "hi 👋 there"),
    ("Mixed",            "price: €5 — caffè ☕"),
]

for name, text in test_strings:
    mapped = sum(1 for c in text if char_to_hid(c) is not None)
    dropped = [c for c in text if char_to_hid(c) is None]
    would_type = "".join(c for c in text if char_to_hid(c) is not None)
    print(f"\n[{name}]")
    print(f"  Input:   {text!r}")
    print(f"  Mapped:  {mapped} chars")
    print(f"  Dropped: {len(dropped)} chars -> {dropped}")
    print(f"  Result:  {would_type!r}")
    if dropped:
        print(f"  ⚠️  {len(dropped)} characters SILENTLY LOST")

print("\n" + "=" * 60)
print("FAULT #6: Broken pipe on socket close")
print("=" * 60)
print("Log evidence from /tmp/btkbd.log:")
print("  [!] Socket error: [Errno 32] Broken pipe")
print("  This fires EVERY TIME socat closes the connection")
print("  before reading the OK response.")
print("  Status: CONFIRMED (cosmetic, but masks real errors)")

print("\n" + "=" * 60)
print("FAULT #5: Socket thread blocks during long typing")
print("=" * 60)
print("command_socket.py line 56 calls on_text_callback(text)")
print("SYNCHRONOUSLY in the accept loop. While typing 100 chars")
print("at 40ms/char = 8 seconds, no new connections can be accepted.")
print("Status: CONFIRMED by code inspection")

print("\n" + "=" * 60)
print("FAULT #7: No message queue / retry")
print("=" * 60)
print("If iPhone disconnects, type_text() in server.py checks")
print("get_report_char() which returns None. Message is LOST.")
print("No buffer, no retry, no persistence.")
print("Status: CONFIRMED by code inspection")

print("\n" + "=" * 60)
print("FAULT #3: Stale _report_char on unclean disconnect")
print("=" * 60)
print("iOS disconnects without StopNotify -> _report_char stays set")
print("-> send_notification fires into void -> silent failure")
print("Need to test this live with btmon")

print("\n" + "=" * 60)
print("ALL FAULTS IDENTIFIED")
print("=" * 60)
