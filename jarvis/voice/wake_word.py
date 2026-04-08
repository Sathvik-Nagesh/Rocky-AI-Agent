"""
Wake word detector — runs in a background thread.

Records 1.5-second audio bursts continuously with a tiny Whisper
model and sets an threading.Event whenever "rocky" is heard.
The main thread blocks on that event instead of recording 5-second
windows blindly, giving Rocky proper always-on listening.
"""
import threading
import tempfile
import os
import logging
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
from faster_whisper import WhisperModel

_SAMPLE_RATE   = 16000
_BURST_SECONDS = 1.5   # Short window — just enough to catch the wake word

class WakeWordDetector:
    """Background thread that fires an Event when 'hey rocky' or 'rocky' is heard."""

    WAKE_PHRASES = {"rocky", "hey rocky", "ok rocky", "yo rocky"}

    def __init__(self):
        self._event  = threading.Event()
        self._stop   = threading.Event()
        self._thread = None

        # Use the ultra-light tiny.en — purpose is speed, not accuracy
        logging.info("Loading wake-word Whisper model (tiny.en)...")
        try:
            self._model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
            logging.info("Wake-word model ready.")
        except Exception as e:
            logging.error(f"Wake-word model failed to load: {e}")
            self._model = None

    # ── public API ────────────────────────────────────────────────────────────

    def start(self):
        """Begin background listening."""
        if self._model is None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background listening."""
        self._stop.set()

    def wait_for_wake(self, timeout: float | None = None) -> bool:
        """Block until wake word is detected. Returns True if fired, False on timeout."""
        fired = self._event.wait(timeout=timeout)
        self._event.clear()
        return fired

    # ── internal ──────────────────────────────────────────────────────────────

    def _listen_loop(self):
        while not self._stop.is_set():
            try:
                recording = sd.rec(
                    int(_BURST_SECONDS * _SAMPLE_RATE),
                    samplerate=_SAMPLE_RATE,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    temp_path = f.name
                    wav_write(temp_path, _SAMPLE_RATE, recording)

                segments, _ = self._model.transcribe(temp_path, beam_size=1)
                text = " ".join(s.text for s in segments).strip().lower()

                if any(phrase in text for phrase in self.WAKE_PHRASES):
                    logging.info(f"Wake word detected: '{text}'")
                    self._event.set()

            except Exception as e:
                logging.debug(f"Wake-word loop error: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
