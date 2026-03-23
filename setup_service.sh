#!/bin/bash
# setup_service.sh — Register wifi_manager as a systemd service
# Run as root: sudo bash setup_service.sh

set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
heading() { echo -e "\n${YELLOW}━━━ $* ━━━${NC}"; }

[ "$(id -u)" -eq 0 ] || error "Run as root: sudo bash setup_service.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_SRC="${SCRIPT_DIR}/wifi_manager.py"
INSTALL_DIR="/opt/wifi_manager"
INSTALL_BIN="${INSTALL_DIR}/wifi_manager.py"
SERVICE_NAME="wifi-manager"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Choose Python environment ─────────────────────────────────────────────────

heading "Python environment"
echo ""
echo "  1) System Python     (/usr/bin/python3)"
echo "  2) Virtual env       (create at ${INSTALL_DIR}/venv)"
echo "  3) Custom path       (enter manually)"
echo ""
read -rp "Choose [1/2/3]: " ENV_CHOICE

case "$ENV_CHOICE" in
  1)
    PYTHON_BIN="/usr/bin/python3"
    PIP_BIN="/usr/bin/pip3"
    USE_VENV=false
    info "Using system Python: $PYTHON_BIN"
    ;;
  2)
    PYTHON_BIN="${INSTALL_DIR}/venv/bin/python3"
    PIP_BIN="${INSTALL_DIR}/venv/bin/pip"
    USE_VENV=true
    info "Will create virtualenv at ${INSTALL_DIR}/venv"
    ;;
  3)
    read -rp "Enter full path to python3 binary: " PYTHON_BIN
    [ -f "$PYTHON_BIN" ] || error "Not found: $PYTHON_BIN"
    PIP_BIN="$(dirname "$PYTHON_BIN")/pip3"
    [ -f "$PIP_BIN" ] || PIP_BIN="$(dirname "$PYTHON_BIN")/pip"
    [ -f "$PIP_BIN" ] || error "pip not found alongside $PYTHON_BIN"
    USE_VENV=false
    info "Using custom Python: $PYTHON_BIN"
    ;;
  *)
    error "Invalid choice"
    ;;
esac

# ── Preflight checks ──────────────────────────────────────────────────────────

heading "Preflight checks"

[ -f "$SCRIPT_SRC" ] || error "wifi_manager.py not found in $SCRIPT_DIR"
info "Found wifi_manager.py"

command -v nmcli &>/dev/null || error "nmcli not found — install network-manager"
info "nmcli $(nmcli --version)"

# ── Install script ────────────────────────────────────────────────────────────

heading "Installing script"
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_SRC" "$INSTALL_BIN"
chmod +x "$INSTALL_BIN"
info "Copied to $INSTALL_BIN"

mkdir -p /var/log
touch /var/log/wifi_manager.log
info "Log file ready at /var/log/wifi_manager.log"

# ── Setup virtualenv if chosen ────────────────────────────────────────────────

if [ "$USE_VENV" = true ]; then
    heading "Creating virtual environment"

    # need python3-venv
    apt-get install -y python3-venv --no-install-recommends
    python3 -m venv "${INSTALL_DIR}/venv"
    info "Virtualenv created at ${INSTALL_DIR}/venv"

    heading "Installing dependencies into venv"
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install flask RPi.GPIO
    info "flask and RPi.GPIO installed into venv"

else
    # ── Check/install deps for system or custom python ────────────────────────
    heading "Checking dependencies"

    if ! "$PYTHON_BIN" -c "import flask" 2>/dev/null; then
        warn "Flask not found — installing…"
        if [ "$ENV_CHOICE" = "1" ]; then
            "$PIP_BIN" install flask --break-system-packages
        else
            "$PIP_BIN" install flask
        fi
    fi
    info "Flask ready"

    if ! "$PYTHON_BIN" -c "import RPi.GPIO" 2>/dev/null; then
        warn "RPi.GPIO not found — installing…"
        if [ "$ENV_CHOICE" = "1" ]; then
            "$PIP_BIN" install RPi.GPIO --break-system-packages
        else
            "$PIP_BIN" install RPi.GPIO
        fi
    fi
    info "RPi.GPIO ready"
fi

# ── Verify final python binary works ─────────────────────────────────────────

"$PYTHON_BIN" -c "import flask, RPi.GPIO" \
  || error "Dependency check failed for $PYTHON_BIN — check install logs above"
info "Python binary verified: $PYTHON_BIN"

# ── Create service file ───────────────────────────────────────────────────────

heading "Creating systemd service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Headless Wi-Fi Setup Manager
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=simple
ExecStart=${PYTHON_BIN} ${INSTALL_BIN}
WorkingDirectory=${INSTALL_DIR}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wifi-manager
User=root

[Install]
WantedBy=multi-user.target
EOF

info "Service file written to $SERVICE_FILE"

# ── Enable and start ──────────────────────────────────────────────────────────

heading "Enabling service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
info "Enabled — will start on every boot"

systemctl restart "${SERVICE_NAME}.service"
sleep 2

if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    info "Service is running"
else
    warn "Service not running — check logs below"
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager
fi

# ── Summary ───────────────────────────────────────────────────────────────────

heading "Done!"
echo ""
echo "  Installed  : ${INSTALL_BIN}"
echo "  Python     : ${PYTHON_BIN}"
echo "  Service    : ${SERVICE_FILE}"
echo ""
echo "  Useful commands:"
echo "    journalctl -u wifi-manager -f        # live logs"
echo "    systemctl status wifi-manager         # service status"
echo "    systemctl restart wifi-manager        # restart"
echo "    systemctl disable wifi-manager        # remove from boot"
echo ""
