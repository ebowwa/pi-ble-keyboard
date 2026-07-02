#!/bin/bash
sleep 2
sudo btmgmt --index 0 power off
sleep 1
sudo btmgmt --index 0 bredr off
sleep 1
sudo btmgmt --index 0 power on
sleep 2
sudo nohup python3 -u /home/pi/bt_keyboard_v5.py > /tmp/bt_keyboard.log 2>&1 &
echo "Pi Keyboard ready (LE-only)"
