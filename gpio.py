# gpio.py — GPIO handling for wifi_manager

import time
import threading
import logging
import RPi.GPIO as GPIO
from config import BUTTON_PIN, BUTTON_HOLD_SEC, LED_PIN

log = logging.getLogger("wifi_manager")

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
    from wifi import stop_ap, delete_saved_wifi_connections, scan_networks, start_ap
    log.info("Factory Wi-Fi reset triggered")
    stop_ap()
    delete_saved_wifi_connections()
    time.sleep(1)
    scan_networks()  # radio is free after AP teardown
    start_ap()       # Flask already running, just bring AP up

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # RPi.GPIO doesn't support both FALLING and RISING on the same pin
    # in one add_event_detect call — use BOTH with the same callback and
    # track state manually.
    GPIO.add_event_detect(
        BUTTON_PIN, GPIO.BOTH,
        callback=lambda ch: _on_press(ch) if not GPIO.input(ch) else _on_release(ch),
        bouncetime=50,
    )

    if LED_PIN is not None:
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.output(LED_PIN, GPIO.LOW)

    log.info(f"GPIO ready — reset button on BCM {BUTTON_PIN} (hold {BUTTON_HOLD_SEC}s)")

def cleanup_gpio():
    GPIO.cleanup()