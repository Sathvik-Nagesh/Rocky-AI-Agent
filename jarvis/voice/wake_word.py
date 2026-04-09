"""
Wake word detector — runs in a background thread.
Replaces heavy Whisper model with openWakeWord (zero-CPU cost).
Continuously records via pyaudio and fires event when "hey jarvis" / "hey rocky" equivalent is heard.
"""
import threading
import os
import logging
import numpy as np

try:
    import pyaudio
    import openwakeword
    from openwakeword.model import Model
    _OWW_AVAILABLE = True
except ImportError:
    _OWW_AVAILABLE = False
    logging.warning("openwakeword or pyaudio missing. Wake word disabled.")

# Best zero-CPU openwakeword pre-trained model out of the box
_WAKE_WORD_MODEL = "hey_jarvis"

class WakeWordDetector:
    """Background thread that fires an Event when the wake word is heard."""

    def __init__(self):
        self._event  = threading.Event()
        self._stop   = threading.Event()
        self._thread = None
        self._model  = None

        if _OWW_AVAILABLE:
            logging.info(f"Loading openWakeWord model ({_WAKE_WORD_MODEL})...")
            try:
                # Disable openwakeword telemetry and download model
                openwakeword.utils.download_models() 
                self._model = Model(wakeword_models=[_WAKE_WORD_MODEL], inference_framework="onnx")
                logging.info("openWakeWord ready.")
            except Exception as e:
                logging.error(f"openWakeWord failed to load: {e}")
                self._model = None

    # ── public API ────────────────────────────────────────────────────────────
    def start(self):
        if self._model is None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def wait_for_wake(self, timeout: float | None = None) -> bool:
        fired = self._event.wait(timeout=timeout)
        self._event.clear()
        return fired

    # ── internal ──────────────────────────────────────────────────────────────
    def _listen_loop(self):
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        CHUNK = 1280

        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        while not self._stop.is_set():
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Feed frame to openwakeword
                prediction = self._model.predict(audio_data)
                
                # Check if the score exceeds the confidence threshold (0.5 is standard)
                for mdl, score in prediction.items():
                    if score > 0.5:
                        logging.info(f"Wake word '{mdl}' detected! (Score: {score:.2f})")
                        self._event.set()
                        # Clear buffer to prevent double triggers
                        self._model.reset()

            except Exception as e:
                logging.debug(f"Wake-word loop error: {e}")

        stream.stop_stream()
        stream.close()
        audio.terminate()
