# Raspberry Pi Headless Wi-Fi Setup Manager

A headless Wi-Fi configuration tool for Raspberry Pi devices (tested on Raspberry Pi Zero 2 W with Raspberry Pi OS Bookworm+). This service automatically creates a captive portal access point when no Wi-Fi is configured, allowing users to connect and set up Wi-Fi through a web interface.

## Features

- **Automatic Portal**: Boots into AP mode if no Wi-Fi connection is saved
- **Web Interface**: Simple, responsive captive portal for network selection
- **Network Scanning**: Real-time Wi-Fi network scanning with signal strength
- **Secure Connections**: Supports WPA2/3 encrypted networks
- **Reset Button**: Physical button (GPIO 17) to reset Wi-Fi settings (hold 3 seconds)
- **LED Indicators**: Optional status LED for connection state
- **Systemd Service**: Runs as a background service that starts on boot
- **NetworkManager Integration**: Uses `nmcli` for reliable Wi-Fi management

## Project Structure

The project is modularized for maintainability:

- `wifi_manager.py` - Main entry point and orchestration
- `config.py` - Configuration constants
- `wifi.py` - NetworkManager operations and Wi-Fi management
- `gpio.py` - GPIO handling for button and LED
- `web.py` - Flask web application and routes
- `portal.html` - HTML template for the captive portal
- `setup_service.sh` - Installation script
- `requirements.txt` - Python dependencies

## Requirements

- Raspberry Pi with Wi-Fi (e.g., Zero 2 W, 3B+, 4B)
- Raspberry Pi OS Bookworm or later (uses NetworkManager)
- Python 3.7+
- Root access for service installation

### Dependencies

- `flask` - Web framework for the portal
- `RPi.GPIO` - GPIO control for button and LED
- `network-manager` - Wi-Fi management (pre-installed on Bookworm)

## Installation

1. **Clone or download** this repository to your Raspberry Pi.

2. **Run the setup script** as root:

   ```bash
   sudo bash setup_service.sh
   ```

   The script will first ask whether to install or uninstall the service. For installation, it will:
   - Prompt for Python environment choice (system, virtualenv, or custom)
   - Install required dependencies
   - Copy files to `/opt/wifi_manager/`
   - Create and enable a systemd service
   - Start the service

3. **Reboot** your Raspberry Pi:
   ```bash
   sudo reboot
   ```

## Uninstallation

To remove the Wi-Fi Manager service completely:

1. Run the setup script again:

   ```bash
   sudo bash setup_service.sh
   ```

2. Choose option 2 (Uninstall service) when prompted.

   The script will:
   - Stop and disable the systemd service
   - Remove the service file
   - Delete the installation directory (`/opt/wifi_manager/`)
   - Remove the log file (`/var/log/wifi_manager.log`)

## Update

To update the Wi-Fi Manager with the latest code and dependencies:

1. Download the latest code to your local machine.

2. Run the setup script:

   ```bash
   sudo bash setup_service.sh
   ```

3. Choose option 3 (Update service) when prompted.

   The script will:
   - Detect the existing Python environment (virtualenv or system Python)
   - Stop the service temporarily
   - Copy updated files
   - Install or upgrade dependencies in the detected environment
   - Restart the service

   **No manual environment choice is needed** — the script automatically uses the same environment from the initial installation.
   - Reload systemd

## Usage

### First-Time Setup

1. Power on the Raspberry Pi with no Ethernet cable.
2. If no Wi-Fi is configured, it will create an access point named "GymDevice-Setup" (password: "gymsetup").
3. Connect to this network from your phone/tablet/computer.
4. Open a web browser - you'll be redirected to the setup portal.
5. Select your Wi-Fi network, enter the password, and click "Connect".
6. The device will connect to your network and the portal will disappear.

### Reset Wi-Fi Settings

- **Physical Reset**: Hold the button connected to GPIO 17 for 3 seconds.
- **Software Reset**: Run `sudo systemctl restart wifi-manager`

### Monitoring

- **Service Status**: `sudo systemctl status wifi-manager`
- **Live Logs**: `sudo journalctl -u wifi-manager -f`
- **Log File**: `/var/log/wifi_manager.log`

## Configuration

Edit `config.py` to customize:

- `BUTTON_PIN`: GPIO pin for reset button (default: 17)
- `BUTTON_HOLD_SEC`: Seconds to hold button for reset (default: 3)
- `LED_PIN`: GPIO pin for status LED (default: None - disabled)
- `AP_SSID`: Access point name (default: "GymDevice-Setup")
- `AP_PASSWORD`: AP password (default: "gymsetup", min 8 chars)
- `AP_IP`: Portal IP address (default: "192.168.4.1")
- `PORTAL_PORT`: Web server port (default: 80)

After changes, restart the service:

```bash
sudo systemctl restart wifi-manager
```

## Troubleshooting

### Service Won't Start

- Check logs: `sudo journalctl -u wifi-manager -n 50`
- Verify NetworkManager is running: `sudo systemctl status NetworkManager`
- Ensure Python dependencies are installed

### Can't Connect to AP

- Check Wi-Fi interface: `nmcli dev status`
- Verify no other services are using wlan0
- Try rebooting

### Portal Not Loading

- Ensure port 80 is free (stop apache/nginx if running)
- Check firewall: `sudo ufw status` (disable if blocking)

### GPIO Issues

- Run as root (services run as root by default)
- Check pin numbering (uses BCM mode)
- Test GPIO: `python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); print('OK')"`

## Development

To run manually for testing:

```bash
sudo python3 wifi_manager.py
```

For development with auto-restart:

```bash
sudo pip3 install flask rpi-lgpio
sudo python3 wifi_manager.py
```

## License

This project is open source. Feel free to modify and distribute.

## Contributing

Pull requests welcome! Please test on actual Raspberry Pi hardware.
