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
import logging
from config import LOG_FILE, PORTAL_PORT
from wifi import is_connected, get_saved_ssid, scan_networks, start_ap
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

    if is_connected():
        current = get_saved_ssid()
        log.info(f"Already connected ({current}) — monitoring button for reset")
        led_pattern("connected")
    else:
        log.info("No Wi-Fi — starting captive portal")
        scan_networks()  # scan while radio is free
        start_ap()       # then bring AP up

    # Always run Flask — portal must be ready for button reset at any time
    app.run(host="0.0.0.0", port=PORTAL_PORT, debug=False, threaded=True, use_reloader=False)

if __name__ == "__main__":
    main()
  .lock   { font-size: 11px; color: #d1d5db; margin-left: 4px; }
  .open   { font-size: 11px; color: #6ee7b7; margin-left: 4px; }
  .submit {
    width: 100%; padding: 12px; background: #7c3aed; color: #fff;
    border: none; border-radius: 10px; font-size: 16px; font-weight: 500;
    cursor: pointer; transition: background .15s; margin-top: 4px;
  }
  .submit:hover:not(:disabled) { background: #6d28d9; }
  .submit:disabled { opacity: .6; cursor: not-allowed; }
  .msg {
    margin-top: 18px; padding: 12px 16px; border-radius: 10px;
    font-size: 14px; line-height: 1.5; display: none;
  }
  .msg.ok  { background: #d1fae5; color: #065f46; display: block; }
  .msg.err { background: #fee2e2; color: #991b1b; display: block; }
  .spinner {
    display: inline-block; width: 14px; height: 14px; border: 2px solid #fff;
    border-top-color: transparent; border-radius: 50%;
    animation: spin .7s linear infinite; vertical-align: middle; margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="card">
  <div class="icon">
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none"
         stroke="#fff" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24">
      <path d="M1.5 8.5a13 13 0 0121 0M5 12a9.5 9.5 0 0114 0M8.5 15.5a6 6 0 017 0M12 19h.01"/>
    </svg>
  </div>
  <h1>Connect to Wi-Fi</h1>
  <p class="sub">Select your network to get this device online</p>

  <div class="field">
    <div class="row">
      <label for="ssid" style="margin:0">Network</label>
      <button class="scan-btn" type="button" onclick="scanNetworks()">↻ Scan again</button>
    </div>
    <select id="ssid" required>
      <option value="">— scanning… —</option>
    </select>
  </div>

  <div class="field" id="passField">
    <label for="password">Password</label>
    <div class="pass-wrap">
      <input type="password" id="password" placeholder="Wi-Fi password" autocomplete="off" autocorrect="off" spellcheck="false">
      <button type="button" class="eye" onclick="togglePass()" title="Show/hide password">&#128065;</button>
    </div>
  </div>

  <button class="submit" id="connectBtn" onclick="doConnect()">Connect</button>
  <div class="msg" id="msg"></div>
</div>
<script>
const ssidEl    = document.getElementById('ssid');
const passEl    = document.getElementById('password');
const passField = document.getElementById('passField');
const btn       = document.getElementById('connectBtn');
const msgEl     = document.getElementById('msg');

let networkMeta = {};

async function scanNetworks() {
  ssidEl.innerHTML = '<option value="">— scanning… —</option>';
  btn.disabled = true;
  try {
    const res  = await fetch('/scan');
    const nets = await res.json();
    networkMeta = {};
    if (!nets.length) {
      ssidEl.innerHTML = '<option value="">No networks found — scan again</option>';
    } else {
      ssidEl.innerHTML = nets.map(n => {
        networkMeta[n.ssid] = n;
        const bars = signalBars(n.signal);
        const lock = n.secure ? '🔒 ' : '';
        return `<option value="${esc(n.ssid)}">${lock}${esc(n.ssid)}  ${bars} ${n.signal}%</option>`;
      }).join('');
    }
  } catch {
    ssidEl.innerHTML = '<option value="">Scan failed — try again</option>';
  }
  btn.disabled = false;
  updatePassField();
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function signalBars(signal) {
  const s = parseInt(signal) || 0;
  if (s >= 75) return '▂▄▆█';
  if (s >= 50) return '▂▄▆·';
  if (s >= 25) return '▂▄··';
  return '▂···';
}

function updatePassField() {
  const meta = networkMeta[ssidEl.value];
  passField.style.display = (meta && !meta.secure) ? 'none' : 'block';
}

ssidEl.addEventListener('change', updatePassField);

function togglePass() {
  passEl.type = passEl.type === 'password' ? 'text' : 'password';
}

function showMsg(type, text) {
  msgEl.className = 'msg ' + type;
  msgEl.innerHTML = text;
}

async function doConnect() {
  const ssid     = ssidEl.value.trim();
  const password = passEl.value;
  if (!ssid) { showMsg('err', 'Please select a network.'); return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Connecting…';
  msgEl.className = 'msg';

  try {
    const res  = await fetch('/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ssid, password })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      showMsg('ok', '✓ Connected! The device will switch to your network. You can close this page.');
      btn.innerHTML = 'Connect';
    } else {
      showMsg('err', '✗ ' + (data.message || 'Connection failed — check password and try again.'));
      btn.disabled = false;
      btn.innerHTML = 'Connect';
    }
  } catch {
    showMsg('err', '✗ Could not reach device. Try again.');
    btn.disabled = false;
    btn.innerHTML = 'Connect';
  }
}

scanNetworks();

</script>
</body>
</html>"""


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(PORTAL_HTML)


# Captive portal detection endpoints — redirect to portal
@app.route("/generate_204")         # Android
@app.route("/gen_204")
@app.route("/hotspot-detect.html")  # iOS / macOS
@app.route("/library/test/success.html")
@app.route("/ncsi.txt")             # Windows
@app.route("/connecttest.txt")
@app.route("/redirect")
def captive():
    return redirect(f"http://{AP_IP}/", code=302)


_cached_networks = []

def scan_networks():
    global _cached_networks
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

@app.route("/scan")
def scan():
    return jsonify(_cached_networks)




@app.route("/connect", methods=["POST"])
def connect_route():
    data     = request.get_json() or {}
    ssid     = data.get("ssid", "").strip()
    password = data.get("password", "").strip()

    if not ssid:
        return jsonify({"status": "error", "message": "No SSID provided."})

    log.info(f"Connect request → {ssid}")

    # Fire connection attempt in background so HTTP response reaches browser
    threading.Thread(target=connect_to_wifi, args=(ssid, password), daemon=True).start()
    return jsonify({"status": "ok"})


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
        led_pattern("connected")
    else:
        err = result.stderr.strip() or result.stdout.strip()
        log.warning(f"Failed to connect to '{ssid}': {err}")
        log.info("Reopening captive portal…")
        nmcli(f'con delete "{ssid}"', check=False)
        scan_networks()  # rescan while radio is free before AP comes back up
        start_ap()

# ─── AP mode via NetworkManager ───────────────────────────────────────────────

AP_CON_NAME = "wifi-setup-portal"


def start_ap():
    """Create (or restart) a NM hotspot connection."""
    log.info("Starting AP (hotspot) mode…")
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
    log.info("Stopping AP…")
    nmcli(f'con down "{AP_CON_NAME}"', check=False)
    nmcli(f'con delete "{AP_CON_NAME}"', check=False)


# ─── LED ──────────────────────────────────────────────────────────────────────

_led_stop  = threading.Event()
_led_thread = None


def led_pattern(mode):
    """
    mode = 'portal'    → fast blink (AP active)
           'connected' → slow pulse (online)
           'off'       → LED off
    """
    global _led_thread, _led_stop
    if LED_PIN is None:
        return
    _led_stop.set()
    if _led_thread:
        _led_thread.join(timeout=1)
    _led_stop = threading.Event()

    intervals = {"portal": 0.15, "connected": 0.8, "off": None}
    interval  = intervals.get(mode)

    if interval is None:
        GPIO.output(LED_PIN, GPIO.LOW)
        return

    def _blink(stop, iv):
        while not stop.is_set():
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(iv)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(iv)

    _led_thread = threading.Thread(target=_blink, args=(_led_stop, interval), daemon=True)
    _led_thread.start()


# ─── GPIO button ──────────────────────────────────────────────────────────────

_press_time = None


def _on_press(channel):
    global _press_time
    _press_time = time.monotonic()


def _on_release(channel):
    global _press_time
    if _press_time is None:
        return
    held = time.monotonic() - _press_time
    _press_time = None
    log.info(f"Button held {held:.1f}s")
    if held >= BUTTON_HOLD_SEC:
        threading.Thread(target=_do_reset, daemon=True).start()


def _do_reset():
    log.info("Factory Wi-Fi reset triggered")
    stop_ap()
    delete_saved_wifi_connections()
    time.sleep(1)
    scan_networks()  # radio is free after AP teardown
    start_ap()       # Flask already running, just bring AP up
    #run server too
  


def _on_button_event(channel):
    if GPIO.input(channel) == GPIO.LOW:
        _on_press(channel)
    else:
        _on_release(channel)


def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # full cleanup of this pin before setting up
    try:
        GPIO.remove_event_detect(BUTTON_PIN)
    except Exception:
        pass
    try:
        GPIO.cleanup(BUTTON_PIN)
    except Exception:
        pass

    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    try:
        GPIO.add_event_detect(
            BUTTON_PIN,
            GPIO.BOTH,
            callback=_on_button_event,
            bouncetime=50,
        )
    except RuntimeError as e:
        log.warning(f"add_event_detect failed ({e}) — retrying after full cleanup")
        GPIO.cleanup()
        time.sleep(1)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            BUTTON_PIN,
            GPIO.BOTH,
            callback=_on_button_event,
            bouncetime=50,
        )

    if LED_PIN is not None:
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)

    log.info(f"GPIO ready — reset button on BCM {BUTTON_PIN} (hold {BUTTON_HOLD_SEC}s)")
# ─── Main ─────────────────────────────────────────────────────────────────────

def shutdown(sig, frame):
    log.info("Shutting down…")
    stop_ap()
    led_pattern("off")
    GPIO.cleanup()
    sys.exit(0)


def main():
    if os.geteuid() != 0:
        sys.exit("ERROR: must run as root (sudo)")

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT,  shutdown)

    setup_gpio()
    time.sleep(15)  # let system settle, NM start, etc.

    if is_connected():
        current = get_saved_ssid()
        log.info(f"Already connected ({current}) — monitoring button for reset")
        led_pattern("connected")
    else:
        log.info("No Wi-Fi — starting captive portal")
        scan_networks()  # scan while radio is free
        start_ap()       # then bring AP up

    # Always run Flask — portal must be ready for button reset at any time
    app.run(host="0.0.0.0", port=PORTAL_PORT, debug=False, threaded=True, use_reloader=False)



if __name__ == "__main__":
    main()
