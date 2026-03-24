# wifi.py — NetworkManager (nmcli) operations for wifi_manager

import subprocess
import time
import logging
from config import AP_INTERFACE, AP_CON_NAME, CONNECT_TIMEOUT

log = logging.getLogger("wifi_manager")

# ─── nmcli helpers ────────────────────────────────────────────────────────────

def nmcli(args, check=True, timeout=30):
    cmd = f"nmcli {args}"
    log.debug(f"$ {cmd}")
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        check=check, timeout=timeout
    )

def is_connected():
    """Return True if wlan0 has an active NM connection."""
    try:
        r = nmcli(f"dev status", check=False)
        for line in r.stdout.splitlines():
            if AP_INTERFACE in line and "connected" in line and "disconnected" not in line:
                return True
    except Exception:
        pass
    return False

def get_saved_ssid():
    """Return the SSID of whichever saved connection is active, or None."""
    try:
        r = nmcli("-t -f NAME,DEVICE con show --active", check=False)
        for line in r.stdout.splitlines():
            name, _, dev = line.partition(":")
            if dev.strip() == AP_INTERFACE:
                return name.strip()
    except Exception:
        pass
    return None

def delete_saved_wifi_connections():
    """Delete all saved Wi-Fi connections (leaves ethernet etc. untouched)."""
    try:
        r = nmcli("-t -f NAME,TYPE con show", check=False)
        for line in r.stdout.splitlines():
            name, _, ctype = line.partition(":")
            if "wireless" in ctype or "wifi" in ctype:
                log.info(f"Deleting saved connection: {name.strip()}")
                nmcli(f'con delete "{name.strip()}"', check=False)
    except Exception as e:
        log.error(f"Error deleting connections: {e}")

def connect_to_wifi(ssid, password):
    from config import AP_INTERFACE, CONNECT_TIMEOUT
    time.sleep(1.5)  # let HTTP response reach browser
    stop_ap()
    time.sleep(1)    # let radio settle into station mode

    # rescan before connect — required on single-band chip
    log.info("Rescanning before connect…")
    nmcli(f"dev wifi rescan ifname {AP_INTERFACE}", check=False, timeout=8)
    time.sleep(3)    # wait for scan cache to populate

    log.info(f"Attempting to connect to '{ssid}'…")
    nmcli(f'con delete "{ssid}"', check=False)

    if password:
        cmd = (
            f'dev wifi connect "{ssid}" '
            f'password "{password}" '
            f'ifname {AP_INTERFACE} '
            f'name "{ssid}"'
        )
    else:
        cmd = (
            f'dev wifi connect "{ssid}" '
            f'ifname {AP_INTERFACE} '
            f'name "{ssid}"'
        )

    result = nmcli(cmd, check=False, timeout=CONNECT_TIMEOUT + 5)

    if result.returncode == 0 and "successfully activated" in result.stdout:
        log.info(f"Connected to '{ssid}' successfully.")
        from gpio import led_pattern
        led_pattern("connected")
    else:
        err = result.stderr.strip() or result.stdout.strip()
        log.warning(f"Failed to connect to '{ssid}': {err}")
        log.info("Reopening captive portal…")
        nmcli(f'con delete "{ssid}"', check=False)
        scan_networks()  # rescan while radio is free before AP comes back up
        start_ap()

# ─── AP mode via NetworkManager ───────────────────────────────────────────────

def start_ap():
    """Create (or restart) a NM hotspot connection."""
    from config import AP_SSID, AP_PASSWORD, AP_IP, AP_INTERFACE, AP_CON_NAME
    log.info("Starting AP (hotspot) mode…")
    from gpio import led_pattern
    led_pattern("portal")

    # Remove stale profile if it exists
    nmcli(f'con delete "{AP_CON_NAME}"', check=False)

    # Build the add command
    add_cmd = (
        f'con add type wifi ifname {AP_INTERFACE} '
        f'con-name "{AP_CON_NAME}" '
        f'ssid "{AP_SSID}" '
        f'-- '
        f'wifi.mode ap '
        f'wifi.band bg '
        f'wifi.channel 6 '
        f'ipv4.method shared '
        f'ipv4.addresses {AP_IP}/24 '
    )

    if AP_PASSWORD:
        add_cmd += (
            f'wifi-sec.key-mgmt wpa-psk '
            f'wifi-sec.psk "{AP_PASSWORD}" '
        )
    else:
        add_cmd += 'wifi-sec.key-mgmt none '

    nmcli(add_cmd)
    nmcli(f'con up "{AP_CON_NAME}"')

    log.info(f"Hotspot '{AP_SSID}' active at {AP_IP}")

def stop_ap():
    """Bring down and delete the hotspot NM connection."""
    from config import AP_CON_NAME
    log.info("Stopping AP…")
    nmcli(f'con down "{AP_CON_NAME}"', check=False)
    nmcli(f'con delete "{AP_CON_NAME}"', check=False)

# ─── Network scanning ─────────────────────────────────────────────────────────

_cached_networks = []

def scan_networks():
    global _cached_networks
    from config import AP_INTERFACE, AP_SSID
    log.info("Scanning for networks…")
    try:
        nmcli(f"dev wifi rescan ifname {AP_INTERFACE}", check=False, timeout=8)
        time.sleep(3)

        result = nmcli(
            f"--fields SSID,SIGNAL,SECURITY dev wifi list ifname {AP_INTERFACE}",
            check=False
        )
        networks = []
        seen = set()
        for line in result.stdout.splitlines()[1:]:  # skip header
            cols = line.split()
            if len(cols) < 2:
                continue
            # last col = SECURITY, second last = SIGNAL, rest = SSID
            security = cols[-1]
            signal   = cols[-2]
            ssid     = " ".join(cols[:-2])

            if not ssid or ssid == "--" or ssid in seen or ssid == AP_SSID:
                continue
            seen.add(ssid)
            networks.append({
                "ssid":   ssid,
                "signal": int(signal) if signal.isdigit() else 0,  # keep 0-100 as-is
                "secure": security != "--",
            })

        networks.sort(key=lambda x: x["signal"], reverse=True)
        _cached_networks = networks
        log.info(f"Found {len(networks)} networks")

    except Exception as e:
        log.error(f"Scan error: {e}")

def get_cached_networks():
    return _cached_networks