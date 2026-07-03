#!/bin/bash
# Force LE-only mode (disable BR/EDR to prevent Classic BT connections)
btmgmt power off
btmgmt bredr off
btmgmt power on
