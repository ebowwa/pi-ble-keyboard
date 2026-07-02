# Pi BLE HID Keyboard

Turn a Raspberry Pi into a **Bluetooth Low Energy keyboard** that types on iOS/iPhone — using pure Boot Protocol over GATT (HOGP).

## Quick Start

### On the Pi

```bash
# 1. Install the package
pip3 install .

# 2. Disable BlueZ input plugin (prevents Classic HID SDP record)
sudo sed -i 's/--noplugin=a2dp,avrcp,hfp,hfpgw/--noplugin=a2dp,avrcp,hfp,hfpgw,input/' \
    /lib/systemd/system/bluetooth.service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth

# 3. Copy and enable the systemd service
sudo cp pi/bt-keyboard.service /etc/systemd/system/
sudo cp pi/start_bt_keyboard.sh /home/pi/
sudo systemctl daemon-reload
sudo systemctl enable bt-keyboard
sudo systemctl start bt-keyboard
```

### Pair on iPhone

Settings → Bluetooth → **Pi Keyboard** → Pair

### Type

```bash
echo "hello world" | socat - UNIX-CONNECT:/tmp/bt_keyboard.sock
```

Or from a remote machine:
```bash
echo "hello world" | ssh pi@<pi-ip> 'socat - UNIX-CONNECT:/tmp/bt_keyboard.sock'
```

## Project Structure

```
pi-ble-keyboard/
├── src/btkeyboard/          # Modular Python package
│   ├── __init__.py          #   Package exports + version
│   ├── __main__.py          #   python -m btkeyboard entry point
│   ├── keymap.py            #   USB HID keymap (char → usage code + modifier)
│   ├── hid_descriptor.py    #   HID Report Map, UUIDs, constants
│   ├── report.py            #   Boot Protocol report encoder (8-byte)
│   ├── typing.py            #   Text → report sequence engine
│   ├── gatt.py              #   BlueZ D-Bus GATT server (Service, Char, Desc)
│   ├── advertisement.py     #   BLE LE advertisement
│   ├── agent.py             #   Pairing agent (auto-accept)
│   ├── command_socket.py    #   Unix socket server for typing input
│   └── server.py            #   Wires everything together + main()
├── tests/                   # 202 tests (keymap, report, HID desc, typing, integration)
├── pi/                      # Pi deployment files
│   ├── start_bt_keyboard.sh #   Startup script (BR/EDR off → LE-only)
│   └── bt-keyboard.service  #   systemd unit
├── archive/                 # Previous iterations (v1–v4) for reference
└── .github/workflows/ci.yml # CI: 202 tests on push
```

## Running Tests

```bash
# Install dev dependencies
pip3 install -e ".[dev]"

# Run all 202 tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=btkeyboard --cov-report=term-missing
```

## The 5 Key Fixes (Lessons Learned)

1. **Disable BR/EDR entirely** (`btmgmt bredr off`) — Without this, iOS connects via Classic Bluetooth and GATT HID notifications are ignored.

2. **Disable BlueZ input plugin** (`--noplugin=input`) — Removes the Classic HID SDP record that tricks iOS into using BR/EDR mode.

3. **Use custom D-Bus paths** (`/pihid/service0` instead of `/org/bluez/hci0/service0`) — BlueZ's own ObjectManager at `/` shadows application objects at the same path.

4. **Pure Boot Protocol** — 8-byte reports with no Report ID prefix. The HID Report Map uses no `0x85` (Report ID) tag. This matches what real BLE keyboards send.

5. **Report Reference descriptor** — Report ID=0, Report Type=Input. iOS requires this descriptor on the Report characteristic to know it's a keyboard input source.

## How It Works

```
                    BLE LE
  iPhone  <──────────────────>  Raspberry Pi
  (iOS)     GATT HID Service     (BlueZ + Python)
             0x1812
```

The Pi registers a GATT application with:
- HID Information (0x2A4A)
- HID Report Map (0x2A4B) — standard keyboard descriptor, no Report ID
- HID Report (0x2A4D) — 8-byte Boot Protocol, notify-enabled
- Report Reference (0x2908) — Report ID=0, Input
- HID Protocol Mode (0x2A4E) — Report Protocol Mode
- HID Control Point (0x2A4C) — Suspend/Resume

Text typed via the Unix socket is converted to HID keycodes and sent as GATT notifications to iOS.

## Requirements

- Raspberry Pi 4 (built-in Bluetooth 5.0)
- BlueZ 5.55+ (`bluetoothd`)
- Python 3.9+ with `dbus-python` and `PyGObject`
- `socat` for the typing interface
- iOS device (iPhone/iPad)

## Troubleshooting

- **"No client subscribed"** — iOS didn't subscribe to notifications. Forget the device on iPhone and pair fresh.
- **Text doesn't appear** — Make sure BR/EDR is off (`sudo btmgmt --index 0 info` should show `le` without `br/edr`).
- **Not discoverable** — Restart the keyboard script. The advertisement may have been released.

## License

MIT
