# config.py

import os

# =========================
# AUDIO MODE
# =========================
# Standard:
# "vlc"  = Desktop-Audio / VLC / Bluetooth-Monitor bevorzugen
# "mic"  = Mikrofon bevorzugen
# "auto" = zuerst VLC-Monitor, sonst Mikrofon
DEFAULT_AUDIO_MODE = "vlc"

# GUI kann diesen Wert überschreiben
AUDIO_MODE = os.getenv("GUI_SELECTED_MODE", DEFAULT_AUDIO_MODE).strip().lower()

# Wenn None, wird automatisch gesucht
FORCE_PULSE_SOURCE_NAME = None

# Bevorzugte Keywords für VLC-/Monitor-Quellen
PREFERRED_VLC_SOURCE_KEYWORDS = [
    "monitor",
    "bluez_output",
    "alsa_output",
    "pipewire",
    "pulse",
]

# Bevorzugte Keywords für Mikrofon-Quellen
PREFERRED_MIC_SOURCE_KEYWORDS = [
    "input",
    "mic",
    "microphone",
    "usb",
    "bluez_input",
]

# Audioformat für parec
PAREC_FORMAT = "s16le"
SAMPLE_RATE = 44100
CHANNELS = 1
BLOCK_SIZE = 1024

# =========================
# LED CONFIG
# =========================
LED_COUNT = 120
LED_PIN = 18              # GPIO18 = physischer Pin 12
LED_FREQ_HZ = 800000
LED_DMA = 10

DEFAULT_LED_BRIGHTNESS = 180
try:
    LED_BRIGHTNESS = int(os.getenv("GUI_SELECTED_BRIGHTNESS", str(DEFAULT_LED_BRIGHTNESS)))
except ValueError:
    LED_BRIGHTNESS = DEFAULT_LED_BRIGHTNESS

LED_BRIGHTNESS = max(0, min(255, LED_BRIGHTNESS))

LED_INVERT = False
LED_CHANNEL = 0

# =========================
# VISUAL / PERFORMANCE
# =========================
FPS = 60
SMOOTHING = 0.78
DECAY = 0.90
NOISE_FLOOR = 0.010

# Auto-Gain
TARGET_LEVEL = 0.22
AUTO_GAIN_ATTACK = 0.18
AUTO_GAIN_RELEASE = 0.02
MIN_DYNAMIC_GAIN = 0.8
MAX_DYNAMIC_GAIN = 6.0

# Frequenz-Booster
BASS_BOOST = 1.35
MID_BOOST = 1.00
TREBLE_BOOST = 1.10

# Visualisierung
BASE_HUE_SHIFT_SPEED = 0.010
SATURATION = 1.0
VALUE_MIN = 0.01
VALUE_MAX = 1.0
SCROLL_SPEED = 0.60

# Frequenz-Mapping
FREQ_MIN = 20
FREQ_MAX = 12000

DEBUG_PRINT_SOURCES = True
STARTUP_TEST_FLASH = False