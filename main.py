# main.py

import math
import time
import signal
import colorsys
import numpy as np

from rpi_ws281x import PixelStrip, Color

from config import (
    AUDIO_MODE,
    LED_COUNT,
    LED_PIN,
    LED_FREQ_HZ,
    LED_DMA,
    LED_BRIGHTNESS,
    LED_INVERT,
    LED_CHANNEL,
    FPS,
    DECAY,
    BASE_HUE_SHIFT_SPEED,
    SATURATION,
    VALUE_MIN,
    VALUE_MAX,
    SCROLL_SPEED,
    FREQ_MIN,
    FREQ_MAX,
    STARTUP_TEST_FLASH,
)
from audio_input import AudioProcessor


running = True


def handle_exit(signum, frame):
    global running
    running = False


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def hsv_to_rgb255(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s), clamp(v))
    return int(r * 255), int(g * 255), int(b * 255)


def rgb_color(r, g, b):
    return Color(int(r), int(g), int(b))


def set_all(strip, r, g, b):
    c = rgb_color(r, g, b)
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, c)
    strip.show()


def startup_flash(strip):
    for color in [(30, 0, 0), (0, 30, 0), (0, 0, 30), (0, 0, 0)]:
        set_all(strip, *color)
        time.sleep(0.15)


def make_log_bins(freqs, spectrum, num_bins, f_min=20, f_max=12000):
    if len(freqs) != len(spectrum):
        raise ValueError("freqs und spectrum müssen gleich lang sein")

    edges = np.logspace(np.log10(f_min), np.log10(f_max), num_bins + 1)
    binned = np.zeros(num_bins, dtype=np.float32)

    for i in range(num_bins):
        lo = edges[i]
        hi = edges[i + 1]
        mask = (freqs >= lo) & (freqs < hi)
        if np.any(mask):
            binned[i] = float(np.mean(spectrum[mask]))

    if num_bins >= 3:
        kernel = np.array([0.18, 0.64, 0.18], dtype=np.float32)
        padded = np.pad(binned, (1, 1), mode="edge")
        binned = np.convolve(padded, kernel, mode="same")[1:-1]

    return np.clip(binned, 0.0, 1.0)


def main():
    global running

    print("=== LED Backend Start ===")
    print(f"AUDIO_MODE: {AUDIO_MODE}")
    print(f"LED_BRIGHTNESS: {LED_BRIGHTNESS}")
    print("=========================")

    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    strip.begin()

    if STARTUP_TEST_FLASH:
        startup_flash(strip)

    audio = AudioProcessor()

    try:
        audio.start()
    except Exception as e:
        print(f"FEHLER beim Starten von Audio: {e}")
        print("Programm wird beendet.")
        set_all(strip, 0, 0, 0)
        return

    freqs = audio.freqs
    display = np.zeros(LED_COUNT, dtype=np.float32)
    hue_offsets = np.linspace(0.0, 0.22, LED_COUNT, dtype=np.float32)

    phase = 0.0
    last_time = time.time()

    info = audio.get_info()
    print("LED Musikvisualisierung läuft.")
    print(f"Aktueller Audio-Modus: {info['actual_mode']}")
    if info["source_info"] is not None:
        print(f"Quelle: {info['source_info']['name']}")
    print("Beenden mit CTRL+C.")

    try:
        while running:
            frame_start = time.time()
            dt = frame_start - last_time
            last_time = frame_start

            spectrum = audio.get_spectrum()
            rms = audio.get_smoothed_rms()

            bins = make_log_bins(
                freqs=freqs,
                spectrum=spectrum,
                num_bins=LED_COUNT,
                f_min=FREQ_MIN,
                f_max=FREQ_MAX,
            )

            phase += SCROLL_SPEED * dt * LED_COUNT
            shifted = np.roll(bins, int(phase) % LED_COUNT)

            wave = np.zeros(LED_COUNT, dtype=np.float32)
            for i in range(LED_COUNT):
                x = i / max(1, LED_COUNT - 1)
                wave[i] = (
                    0.08 * math.sin((x * 7.0) + phase * 0.05)
                    + 0.05 * math.sin((x * 17.0) - phase * 0.03)
                    + 0.03 * math.sin((x * 31.0) + phase * 0.02)
                )

            target = np.clip(shifted + wave + (rms * 0.18), 0.0, 1.0)
            display = np.maximum(display * DECAY, target)

            loudness_boost = clamp(0.28 + rms * 2.8, 0.15, 1.0)
            base_hue = (frame_start * BASE_HUE_SHIFT_SPEED) % 1.0

            for i in range(LED_COUNT):
                intensity = float(display[i])
                intensity = intensity ** 1.15

                hue = (base_hue + hue_offsets[i] + intensity * 0.10) % 1.0
                value = clamp(VALUE_MIN + intensity * loudness_boost, VALUE_MIN, VALUE_MAX)

                r, g, b = hsv_to_rgb255(hue, SATURATION, value)
                strip.setPixelColor(i, rgb_color(r, g, b))

            strip.show()

            elapsed = time.time() - frame_start
            sleep_time = max(0.0, (1.0 / FPS) - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        pass
    finally:
        audio.stop()
        set_all(strip, 0, 0, 0)
        print("LEDs ausgeschaltet. Programm beendet.")


if __name__ == "__main__":
    main()