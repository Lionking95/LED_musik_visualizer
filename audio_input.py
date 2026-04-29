# audio_input.py
#hallo
import subprocess
import threading
import time
import numpy as np
import sounddevice as sd

from config import (
    AUDIO_MODE,
    FORCE_PULSE_SOURCE_NAME,
    PREFERRED_VLC_SOURCE_KEYWORDS,
    PREFERRED_MIC_SOURCE_KEYWORDS,
    PAREC_FORMAT,
    SAMPLE_RATE,
    CHANNELS,
    BLOCK_SIZE,
    SMOOTHING,
    NOISE_FLOOR,
    TARGET_LEVEL,
    AUTO_GAIN_ATTACK,
    AUTO_GAIN_RELEASE,
    MIN_DYNAMIC_GAIN,
    MAX_DYNAMIC_GAIN,
    BASS_BOOST,
    MID_BOOST,
    TREBLE_BOOST,
    DEBUG_PRINT_SOURCES,
)


def _safe_lower(value):
    return str(value).strip().lower()


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def list_pulse_sources():
    code, out, err = run_command(["pactl", "list", "sources", "short"])
    if code != 0:
        raise RuntimeError(f"pactl list sources short fehlgeschlagen: {err.strip()}")

    sources = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        source_name = parts[1]
        sources.append({
            "raw": line,
            "name": source_name,
        })

    return sources


def print_pulse_sources():
    print("\n=== Verfügbare Pulse/PipeWire Sources ===")
    try:
        sources = list_pulse_sources()
        if not sources:
            print("Keine Sources gefunden.")
        else:
            for idx, src in enumerate(sources):
                print(f"[{idx}] {src['raw']}")
    except Exception as e:
        print(f"Fehler beim Auflisten der Sources: {e}")
    print("========================================\n")


def score_source(name, keywords):
    name_l = _safe_lower(name)
    score = 0
    for keyword in keywords:
        if _safe_lower(keyword) in name_l:
            score += 10
    return score


def find_vlc_source():
    sources = list_pulse_sources()
    if not sources:
        return None

    if FORCE_PULSE_SOURCE_NAME:
        for src in sources:
            if src["name"] == FORCE_PULSE_SOURCE_NAME:
                return src

    best = None
    best_score = -1

    for src in sources:
        name = src["name"]
        name_l = _safe_lower(name)

        score = score_source(name, PREFERRED_VLC_SOURCE_KEYWORDS)

        if "monitor" in name_l:
            score += 40
        if "bluez_output" in name_l:
            score += 30
        if "alsa_output" in name_l:
            score += 20
        if "pipewire" in name_l:
            score += 10
        if "pulse" in name_l:
            score += 5

        if "input" in name_l:
            score -= 20

        if score > best_score:
            best_score = score
            best = src

    if best_score <= 0:
        return None
    return best


def find_mic_source():
    sources = list_pulse_sources()
    if not sources:
        return None

    best = None
    best_score = -1

    for src in sources:
        name = src["name"]
        name_l = _safe_lower(name)

        score = score_source(name, PREFERRED_MIC_SOURCE_KEYWORDS)

        if "bluez_input" in name_l:
            score += 30
        if "input" in name_l:
            score += 20
        if "mic" in name_l or "microphone" in name_l:
            score += 20
        if "usb" in name_l:
            score += 10

        if "monitor" in name_l:
            score -= 20

        if score > best_score:
            best_score = score
            best = src

    if best_score <= 0:
        return None
    return best


def resolve_audio_source():
    if DEBUG_PRINT_SOURCES:
        print_pulse_sources()

    mode = _safe_lower(AUDIO_MODE)

    if mode == "vlc":
        src = find_vlc_source()
        if src is not None:
            return "vlc", src

        mic = find_mic_source()
        if mic is not None:
            print("WARNUNG: Kein VLC-Monitor gefunden. Fallback auf Mikrofon.")
            return "mic", mic

        raise RuntimeError("Weder VLC-Monitor noch Mikrofon-Source gefunden.")

    if mode == "mic":
        mic = find_mic_source()
        if mic is not None:
            return "mic", mic

        vlc = find_vlc_source()
        if vlc is not None:
            print("WARNUNG: Kein Mikrofon gefunden. Fallback auf VLC-Monitor.")
            return "vlc", vlc

        raise RuntimeError("Weder Mikrofon noch VLC-Monitor-Source gefunden.")

    if mode == "auto":
        vlc = find_vlc_source()
        if vlc is not None:
            return "vlc", vlc

        mic = find_mic_source()
        if mic is not None:
            return "mic", mic

        raise RuntimeError("Im AUTO-Modus wurde keine passende Source gefunden.")

    raise RuntimeError(f"Ungültiger AUDIO_MODE: {AUDIO_MODE}")


class AudioProcessor:
    def __init__(self):
        self.lock = threading.Lock()

        self.latest_spectrum = np.zeros(BLOCK_SIZE // 2 + 1, dtype=np.float32)
        self.prev_spectrum = np.zeros(BLOCK_SIZE // 2 + 1, dtype=np.float32)

        self.latest_rms = 0.0
        self.smoothed_rms = 0.0
        self.dynamic_gain = 1.0

        self.window = np.hanning(BLOCK_SIZE).astype(np.float32)
        self.freqs = np.fft.rfftfreq(BLOCK_SIZE, d=1.0 / SAMPLE_RATE)

        self.running = False
        self.thread = None
        self.process = None

        self.actual_mode = None
        self.source_info = None

    def _process_chunk(self, mono):
        mono = mono.astype(np.float32)

        raw_rms = float(np.sqrt(np.mean(np.square(mono)) + 1e-12))

        if raw_rms > 1e-6:
            target_gain = TARGET_LEVEL / max(raw_rms, 1e-6)
            target_gain = max(MIN_DYNAMIC_GAIN, min(MAX_DYNAMIC_GAIN, target_gain))

            if target_gain > self.dynamic_gain:
                self.dynamic_gain = (
                    (1.0 - AUTO_GAIN_ATTACK) * self.dynamic_gain
                    + AUTO_GAIN_ATTACK * target_gain
                )
            else:
                self.dynamic_gain = (
                    (1.0 - AUTO_GAIN_RELEASE) * self.dynamic_gain
                    + AUTO_GAIN_RELEASE * target_gain
                )

        mono *= self.dynamic_gain
        mono = np.clip(mono, -1.0, 1.0)

        rms = float(np.sqrt(np.mean(np.square(mono)) + 1e-12))
        self.smoothed_rms = self.smoothed_rms * 0.85 + rms * 0.15

        windowed = mono * self.window
        spectrum = np.abs(np.fft.rfft(windowed))

        spectrum = np.log1p(spectrum * 3.0)
        spectrum = np.maximum(spectrum - NOISE_FLOOR, 0.0)

        bass_mask = (self.freqs >= 20) & (self.freqs < 180)
        mid_mask = (self.freqs >= 180) & (self.freqs < 2000)
        treble_mask = self.freqs >= 2000

        spectrum[bass_mask] *= BASS_BOOST
        spectrum[mid_mask] *= MID_BOOST
        spectrum[treble_mask] *= TREBLE_BOOST

        max_val = float(np.max(spectrum)) if spectrum.size else 1.0
        if max_val > 1e-6:
            spectrum /= max_val

        spectrum = SMOOTHING * self.prev_spectrum + (1.0 - SMOOTHING) * spectrum
        self.prev_spectrum = spectrum

        with self.lock:
            self.latest_spectrum = spectrum.copy()
            self.latest_rms = rms

    def _reader_loop_parec(self):
        bytes_per_sample = 2  # s16le
        chunk_bytes = BLOCK_SIZE * CHANNELS * bytes_per_sample

        cmd = [
            "parec",
            "-d",
            self.source_info["name"],
            f"--format={PAREC_FORMAT}",
            f"--rate={SAMPLE_RATE}",
            f"--channels={CHANNELS}",
            "--raw",
        ]

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )

        try:
            while self.running:
                data = self.process.stdout.read(chunk_bytes)
                if not data or len(data) < chunk_bytes:
                    time.sleep(0.01)
                    continue

                mono = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                if CHANNELS > 1:
                    mono = mono.reshape(-1, CHANNELS).mean(axis=1)

                self._process_chunk(mono)

        finally:
            if self.process is not None:
                try:
                    self.process.terminate()
                except Exception:
                    pass
                self.process = None

    def _reader_loop_sounddevice(self):
        def callback(indata, frames, time_info, status):
            mono = indata[:, 0].astype(np.float32)
            self._process_chunk(mono)

        device_index = self.source_info["device_index"]

        stream = sd.InputStream(
            device=device_index,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=callback,
        )

        self.process = stream

        try:
            stream.start()
            while self.running:
                time.sleep(0.05)
        finally:
            try:
                stream.stop()
            except Exception:
                pass
            try:
                stream.close()
            except Exception:
                pass
            self.process = None

    def _resolve_sounddevice_mic(self):
        devices = sd.query_devices()
        best = None

        for idx, dev in enumerate(devices):
            max_in = int(dev.get("max_input_channels", 0))
            if max_in <= 0:
                continue

            name = str(dev.get("name", ""))
            name_l = name.lower()

            score = 0
            if "mic" in name_l or "microphone" in name_l:
                score += 20
            if "usb" in name_l:
                score += 10
            if "input" in name_l:
                score += 5
            if "monitor" in name_l:
                score -= 10

            if best is None or score > best["score"]:
                best = {"device_index": idx, "name": name, "score": score}

        return best

    def start(self):
        if self.running:
            return

        self.actual_mode, self.source_info = resolve_audio_source()

        print("=== Audio-Start ===")
        print(f"Konfigurierter Modus: {AUDIO_MODE}")
        print(f"Tatsächlich verwendeter Modus: {self.actual_mode}")
        print(f"Audio-Source: {self.source_info['name']}")
        print("===================")

        self.running = True

        # VLC/Monitor immer über parec lesen
        if self.actual_mode == "vlc":
            self.thread = threading.Thread(target=self._reader_loop_parec, daemon=True)
            self.thread.start()
            return

        # Mic zuerst über sounddevice versuchen, sonst parec
        if self.actual_mode == "mic":
            try:
                sd_mic = self._resolve_sounddevice_mic()
                if sd_mic is not None:
                    self.source_info = sd_mic
                    print(f"Mic über sounddevice: {sd_mic['name']}")
                    self.thread = threading.Thread(target=self._reader_loop_sounddevice, daemon=True)
                    self.thread.start()
                    return
            except Exception:
                pass

            print("Mic über sounddevice nicht verfügbar, nutze parec-Source.")
            self.thread = threading.Thread(target=self._reader_loop_parec, daemon=True)
            self.thread.start()
            return

    def stop(self):
        self.running = False

        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def get_spectrum(self):
        with self.lock:
            return self.latest_spectrum.copy()

    def get_rms(self):
        with self.lock:
            return float(self.latest_rms)

    def get_smoothed_rms(self):
        with self.lock:
            return float(self.smoothed_rms)

    def get_info(self):
        return {
            "actual_mode": self.actual_mode,
            "source_info": self.source_info,
        }