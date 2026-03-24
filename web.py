# web.py — Flask web portal for wifi_manager

import threading
import logging
from flask import Flask, request, jsonify, render_template_string, redirect, send_from_directory
from wifi import connect_to_wifi, get_cached_networks
from config import AP_IP,CONFIG_PORTAL_PIN

log = logging.getLogger("wifi_manager")

# ─── Flask portal ─────────────────────────────────────────────────────────────

app = Flask(__name__)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    with open('portal.html', 'r') as f:
        html = f.read()
    return render_template_string(html, pin_data=CONFIG_PORTAL_PIN)

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

@app.route("/scan")
def scan():
    return jsonify(get_cached_networks())

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


@app.route("/pi_innov.jpeg")
def logo():
    return send_from_directory('.', 'pi_innov.jpeg')