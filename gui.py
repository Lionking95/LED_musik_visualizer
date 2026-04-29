# gui.py
# Hallo

import os
import signal
import subprocess
import time
from guizero import App, Text, PushButton, Combo, Slider, Box, Drawing
from audio_input import AudioProcessor
from config import AUDIO_MODE, LED_BRIGHTNESS


class LedGuiApp:
    def __init__(self):
        self.led_process = None
        self.audio = None
        self.audio_started = False
        self.current_mode = AUDIO_MODE
        self.current_brightness = LED_BRIGHTNESS

        self.app = App(
            title="LED Musikvisualisierung Control Panel",
            width=1100,
            height=700,
            bg="#111111",
        )

        self.header = Text(
            self.app,
            text="LED Musikvisualisierung",
            size=24,
            color="white",
            font="Arial",
        )

        self.main_box = Box(self.app, layout="grid", width="fill", height="fill")

        # =========================
        # LINKE SEITE - Controls
        # =========================
        self.left_box = Box(self.main_box, grid=[0, 0], layout="auto", width=320)
        self.left_box.bg = "#1b1b1b"

        Text(self.left_box, text="Steuerung", size=18, color="white")

        Text(self.left_box, text="Modus", color="white")
        self.mode_combo = Combo(
            self.left_box,
            options=["vlc", "mic", "auto"],
            selected=self.current_mode,
            width=20,
            command=self.on_mode_change,
        )

        Text(self.left_box, text="Brightness", color="white")
        self.brightness_slider = Slider(
            self.left_box,
            start=10,
            end=255,
            command=self.on_brightness_change,
            width=250,
        )
        self.brightness_slider.value = self.current_brightness

        self.brightness_value = Text(
            self.left_box,
            text=f"Helligkeit: {self.current_brightness}",
            color="white",
        )

        self.start_button = PushButton(
            self.left_box,
            text="LED-Projekt starten",
            command=self.start_led_project,
            width=22,
        )

        self.stop_button = PushButton(
            self.left_box,
            text="LED-Projekt stoppen",
            command=self.stop_led_project,
            width=22,
        )

        self.restart_button = PushButton(
            self.left_box,
            text="Neu starten",
            command=self.restart_led_project,
            width=22,
        )

        self.status_text = Text(
            self.left_box,
            text="Status: GUI läuft",
            color="lightgreen",
        )

        self.led_status_text = Text(
            self.left_box,
            text="LED Backend: gestoppt",
            color="orange",
        )

        self.audio_mode_text = Text(
            self.left_box,
            text=f"Audio-Modus: {self.current_mode}",
            color="white",
        )

        self.audio_source_text = Text(
            self.left_box,
            text="Quelle: wird ermittelt...",
            color="white",
        )

        self.rms_text = Text(
            self.left_box,
            text="Lautstärke: 0.000",
            color="white",
        )

        self.band_text = Text(
            self.left_box,
            text="Bass: 0.00 | Mid: 0.00 | Treble: 0.00",
            color="white",
        )

        # =========================
        # RECHTE SEITE - Visualizer
        # =========================
        self.right_box = Box(self.main_box, grid=[1, 0], layout="auto", width=740)
        self.right_box.bg = "#101010"

        Text(self.right_box, text="Live Visualisierung", size=18, color="white")

        self.drawing = Drawing(
            self.right_box,
            width=720,
            height=520,
            bg="#000000",
        )

        self.footer = Text(
            self.app,
            text="guizero Control Panel für LED + Audio Visualisierung",
            color="#bbbbbb",
            size=10,
        )

        self.setup_audio_monitor()
        self.app.repeat(60, self.update_visualizer)
        self.app.when_closed = self.on_close

    def setup_audio_monitor(self):
        try:
            self.audio = AudioProcessor()
            self.audio.start()
            self.audio_started = True

            info = self.audio.get_info()
            actual_mode = info.get("actual_mode", "unbekannt")
            source_info = info.get("source_info", {})

            source_name = "unbekannt"
            if source_info and "name" in source_info:
                source_name = source_info["name"]

            self.audio_mode_text.value = f"Audio-Modus: {actual_mode}"
            self.audio_source_text.value = f"Quelle: {source_name}"
            self.status_text.value = "Status: Audio-Monitor aktiv"
            self.status_text.text_color = "lightgreen"

        except Exception as e:
            self.audio_started = False
            self.status_text.value = f"Audio-Fehler: {e}"
            self.status_text.text_color = "red"
            self.audio_source_text.value = "Quelle: nicht verfügbar"

    def on_mode_change(self, value):
        self.current_mode = value
        self.audio_mode_text.value = f"Audio-Modus: {value}"

    def on_brightness_change(self, value):
        try:
            self.current_brightness = int(value)
        except Exception:
            self.current_brightness = LED_BRIGHTNESS
        self.brightness_value.value = f"Helligkeit: {self.current_brightness}"

    def start_led_project(self):
        if self.led_process is not None and self.led_process.poll() is None:
            self.led_status_text.value = "LED Backend: läuft bereits"
            self.led_status_text.text_color = "yellow"
            return

        try:
            env = os.environ.copy()
            env["GUI_SELECTED_MODE"] = self.current_mode
            env["GUI_SELECTED_BRIGHTNESS"] = str(self.current_brightness)

            self.led_process = subprocess.Popen(
                ["./start.sh"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env=env,
            )

            self.led_status_text.value = "LED Backend: gestartet"
            self.led_status_text.text_color = "lightgreen"

        except Exception as e:
            self.led_status_text.value = f"LED Startfehler: {e}"
            self.led_status_text.text_color = "red"

    def stop_led_project(self):
        try:
            if self.led_process is not None and self.led_process.poll() is None:
                self.led_process.terminate()
                time.sleep(0.5)

                if self.led_process.poll() is None:
                    self.led_process.kill()

                self.led_status_text.value = "LED Backend: gestoppt"
                self.led_status_text.text_color = "orange"
            else:
                subprocess.run(
                    ["./stop_led.sh"],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    check=False,
                )
                self.led_status_text.value = "LED Backend: Stop-Signal gesendet"
                self.led_status_text.text_color = "orange"

        except Exception as e:
            self.led_status_text.value = f"LED Stopfehler: {e}"
            self.led_status_text.text_color = "red"

    def restart_led_project(self):
        self.stop_led_project()
        time.sleep(0.8)
        self.start_led_project()

    def get_band_levels(self, spectrum, freqs):
        bass_mask = (freqs >= 20) & (freqs < 180)
        mid_mask = (freqs >= 180) & (freqs < 2000)
        treble_mask = freqs >= 2000

        bass = float(spectrum[bass_mask].mean()) if bass_mask.any() else 0.0
        mid = float(spectrum[mid_mask].mean()) if mid_mask.any() else 0.0
        treble = float(spectrum[treble_mask].mean()) if treble_mask.any() else 0.0

        return bass, mid, treble

    def update_visualizer(self):
        self.drawing.clear()

        if not self.audio_started or self.audio is None:
            self.drawing.text(250, 250, "Kein Audio verfügbar", color="white", size=18)
            return

        try:
            spectrum = self.audio.get_spectrum()
            rms = self.audio.get_smoothed_rms()
            freqs = self.audio.freqs

            bass, mid, treble = self.get_band_levels(spectrum, freqs)

            self.rms_text.value = f"Lautstärke: {rms:.3f}"
            self.band_text.value = (
                f"Bass: {bass:.2f} | Mid: {mid:.2f} | Treble: {treble:.2f}"
            )

            width = 720
            height = 520
            num_bars = 64

            if len(spectrum) < num_bars:
                num_bars = max(8, len(spectrum))

            step = max(1, len(spectrum) // num_bars)
            bar_width = width / num_bars

            for i in range(num_bars):
                start = i * step
                end = min(len(spectrum), start + step)
                if start >= len(spectrum):
                    break

                value = float(spectrum[start:end].mean()) if end > start else 0.0
                value = max(0.0, min(1.0, value))

                bar_height = value * (height - 80)
                x1 = i * bar_width + 2
                y1 = height - bar_height - 20
                x2 = (i + 1) * bar_width - 2
                y2 = height - 20

                # Farbverlauf von cyan zu magenta
                r = int(80 + 175 * value)
                g = int(100 + 100 * (1.0 - value))
                b = int(180 + 75 * value)

                color = f"#{r:02x}{g:02x}{b:02x}"
                self.drawing.rectangle(x1, y1, x2, y2, color=color)

            # RMS-Kreis in der Mitte
            circle_size = max(20, min(140, int(40 + rms * 220)))
            cx = width // 2
            cy = 120
            self.drawing.oval(
                cx - circle_size,
                cy - circle_size,
                cx + circle_size,
                cy + circle_size,
                color="#44ccff",
            )

            # Textinfos
            self.drawing.text(
                20,
                20,
                f"Mode: {self.current_mode}",
                color="white",
                size=12,
            )
            self.drawing.text(
                20,
                42,
                f"Brightness: {self.current_brightness}",
                color="white",
                size=12,
            )

        except Exception as e:
            self.status_text.value = f"Visualizer-Fehler: {e}"
            self.status_text.text_color = "red"

    def on_close(self):
        try:
            if self.audio is not None:
                self.audio.stop()
        except Exception:
            pass

        try:
            if self.led_process is not None and self.led_process.poll() is None:
                self.led_process.terminate()
        except Exception:
            pass

        self.app.destroy()

    def run(self):
        self.app.display()


if __name__ == "__main__":
    LedGuiApp().run()
    