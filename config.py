# config.py — Configuration constants for wifi_manager

# GPIO Configuration
BUTTON_PIN = 17             # BCM GPIO pin for reset button
BUTTON_HOLD_SEC = 3         # seconds to hold for reset
LED_PIN = 18              # BCM GPIO pin for status LED, or None

# Access Point Configuration
AP_SSID = "GymDevice-Setup"
AP_PASSWORD = "gymsetup"    # min 8 chars; "" for open network
AP_IP = "192.168.4.1"
AP_INTERFACE = "wlan0"
AP_CON_NAME = "wifi-setup-portal"

# Web Portal Configuration
PORTAL_PORT = 80
CONFIG_PORTAL_PIN = "4455"  # PIN to display on portal for verification

# Logging Configuration
LOG_FILE = "/var/log/wifi_manager.log"

# Network Configuration
CONNECT_TIMEOUT = 20        # seconds to wait for nmcli to connect