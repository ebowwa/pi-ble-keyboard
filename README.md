# Pi BLE HID Keyboard

Turn a Raspberry Pi into a BLE LE keyboard that types on iOS/iPhone.

## What This Does

A Raspberry Pi 4 emulates a Bluetooth HID keyboard using BlueZ's GATT API.
The Pi advertises as a BLE LE peripheral, iOS pairs with it, and you can
type text from the command line that appears on the iPhone's screen.

## How To Type

```bash
echo "hello world" | socat - UNIX-CONNECT:/tmp/bt_keyboard.sock
```

Or from a remote machine:
```bash
echo "hello world" | ssh pi@<pi-ip> 'socat - UNIX-CONNECT:/tmp/bt_keyboard.sock'
```

## Requirements

- Raspberry Pi 4 (built-in Bluetooth 5.0)
- BlueZ 5.55+ (`bluetoothd`)
- Python 3 with `dbus-python` and `PyGObject`
- `socat` for the typing interface
- iOS device (iPhone/iPad)

## Installation

1. **Copy scripts to the Pi:**
   ```bash
   scp bt_keyboard_v5.py pi@<ip>:/home/pi/
   scp start_bt_keyboard.sh pi@<ip>:/home/pi/
   ```

2. **Disable BlueZ input plugin** (prevents Classic HID SDP record):
   ```bash
   sudo sed -i 's/--noplugin=a2dp,avrcp,hfp,hfpgw/--noplugin=a2dp,avrcp,hfp,hfpgw,input/'      /lib/systemd/system/bluetooth.service
   sudo systemctl daemon-reload
   sudo systemctl restart bluetooth
   ```

3. **Install systemd service:**
   ```bash
   sudo cp bt-keyboard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable bt-keyboard
   ```

4. **Pair on iPhone:**
   - Settings → Bluetooth → Pair "Pi Keyboard"
   - Open a text field (Notes, Messages, etc.)

5. **Type:**
   ```bash
   echo "hello from pi" | socat - UNIX-CONNECT:/tmp/bt_keyboard.sock
   ```

## The 5 Key Fixes (Lessons Learned)

1. **Disable BR/EDR entirely** (`btmgmt bredr off`) — Without this, iOS connects
   via Classic Bluetooth and GATT HID notifications are ignored.

2. **Disable BlueZ input plugin** (`--noplugin=input`) — Removes the Classic HID
   SDP record that tricks iOS into using BR/EDR mode.

3. **Use custom D-Bus paths** (`/pihid/service0` instead of
   `/org/bluez/hci0/service0`) — BlueZ's own ObjectManager at `/` shadows
   application objects at the same path.

4. **Pure Boot Protocol** — 8-byte reports with no Report ID prefix. The HID
   Report Map uses no `0x85` (Report ID) tag. This matches what real BLE
   keyboards send.

5. **Report Reference descriptor** — Report ID=0, Report Type=Input. iOS
   requires this descriptor on the Report characteristic to know it's a
   keyboard input source.

## How It Works

```
                    BLE LE
  iPhone  <──────────────────>  Raspberry Pi
  (iOS)     GATT HID Service     (BlueZ + Python)
             0x1812
```

The Pi registers a GATT application with:
- HID Information (0x2A4A)
- HID Report Map (0x2A4B) — standard keyboard descriptor
- HID Report (0x2A4D) — 8-byte Boot Protocol, notify-enabled
- Report Reference (0x2908) — Report ID=0, Input
- HID Protocol Mode (0x2A4E) — Report Protocol Mode
- HID Control Point (0x2A4C) — Suspend/Resume

Text typed via the Unix socket is converted to HID keycodes and sent as
GATT notifications to iOS.

## Files

| File | Description |
|------|-------------|
| `bt_keyboard_v5.py` | Main BLE HID keyboard script (WORKING) |
| `start_bt_keyboard.sh` | Startup script (disables BR/EDR, starts keyboard) |
| `bt-keyboard.service` | systemd service file |
| `archive/` | Earlier versions kept for reference |

## Troubleshooting

- **"No client subscribed"** — iOS didn't subscribe to notifications. Forget
  the device on iPhone and pair fresh.
- **Text doesn't appear** — Make sure BR/EDR is off (`sudo btmgmt --index 0 info`
  should show `le` without `br/edr`).
- **Not discoverable** — Restart the keyboard script. The advertisement may
  have been released.

## License

MIT
