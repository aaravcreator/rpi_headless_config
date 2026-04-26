#!/usr/bin/env python3
"""
wifi_manager.py — Headless Wi-Fi setup for Raspberry Pi Zero 2 W
Uses NetworkManager (nmcli) — compatible with Raspberry Pi OS Bookworm+

Behaviour:
  - Boot with no saved Wi-Fi → opens captive portal AP
  - Button held 3s           → deletes saved connections, reopens portal
  - User submits portal form → nmcli connects, AP tears down
"""

import os
import sys
import signal
import time
import logging
from config import LOG_FILE, PORTAL_PORT
from wifi import is_connected, get_saved_ssid, scan_networks, start_ap, reconnect_to_saved
from gpio import setup_gpio, led_pattern, cleanup_gpio
from web import app

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("wifi_manager")

# ─── Main ─────────────────────────────────────────────────────────────────────

def shutdown(sig, frame):
    log.info("Shutting down…")
    from wifi import stop_ap
    stop_ap()
    led_pattern("off")
    cleanup_gpio()
    sys.exit(0)

def main():
    if os.geteuid() != 0:
        sys.exit("ERROR: must run as root (sudo)")

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT,  shutdown)

    setup_gpio()

    # Try to reconnect to saved networks first
    # reconnect_to_saved()
    time.sleep(10)  # give connection time to stabilize
    
    if is_connected():
        current = get_saved_ssid()
        log.info(f"Already connected ({current}) — monitoring button for reset")
        led_pattern("connected")
    else:
        log.info("No Wi-Fi Connected")
        # scan_networks()  # scan while radio is free
        # start_ap()       # then bring AP up

    # Always run Flask — portal must be ready for button reset at any time
    app.run(host="0.0.0.0", port=PORTAL_PORT, debug=False, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
 